import time
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import (
    FindingEvidence,
    FindingResponse,
    ScanExportResponse,
    ScanListResponse,
    ScanMetadata,
    ScanRequest,
    ScanResponse,
    create_scan_response,
)
from app.collector.collector import CollectorError, collect
from app.core.config import settings
from app.core.ssrf_guard import SSRFGuardError, check_ssrf
from app.core.url_validator import URLValidationError, canonicalize_url
from app.db.models import Scan
from app.db.repository import (
    count_scans,
    create_finding,
    create_scan,
    get_scan,
    get_scans,
    update_scan_completed,
)
from app.db.session import get_db
from app.features.extractor import extract_features
from app.rules import registry
from app.scoring.risk import (
    calculate_risk_score,
    determine_risk_tier,
    map_category,
    map_severity,
    map_source,
)

# Alias for backwards compatibility with tests that mock fetch
fetch = collect

router = APIRouter(prefix="/scans", tags=["scans"])

# Simple in-memory sliding-window rate limiter for scan creation. This bounds
# resource consumption per client; a production deployment would move this to
# a shared store (e.g. Redis) when running multiple workers.
_rate_limit_buckets: dict[str, list[float]] = {}


def _check_rate_limit(client_ip: str) -> None:
    now = time.monotonic()
    window = settings.SCAN_RATE_LIMIT_WINDOW_SECONDS
    bucket = _rate_limit_buckets.get(client_ip)
    if bucket is None:
        bucket = []
        _rate_limit_buckets[client_ip] = bucket
    bucket[:] = [t for t in bucket if now - t < window]
    if len(bucket) >= settings.SCAN_RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many scan requests. Please wait before trying again.",
        )
    bucket.append(now)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("", response_model=ScanResponse, status_code=status.HTTP_200_OK)
async def create_scan_endpoint(
    request: Request, scan_request: ScanRequest, db: AsyncSession = Depends(get_db)
) -> ScanResponse:
    _check_rate_limit(_client_ip(request))

    try:
        validated_url = canonicalize_url(scan_request.url)
    except URLValidationError as e:
        scan = await create_scan(
            db=db,
            url=scan_request.url,
            canonical_url=scan_request.url,
            feature_schema_version="features-v1",
        )
        await update_scan_completed(
            db=db,
            scan_id=scan.id,
            status="failed",
            error_code=e.code,
            error_message=str(e),
        )
        return create_scan_response(
            scan_id=scan.id,
            status="failed",
            error=str(e),
            error_code=e.code,
            created_at=scan.created_at,
        )

    try:
        resolved_ip = check_ssrf(validated_url)
    except SSRFGuardError as e:
        scan = await create_scan(
            db=db,
            url=scan_request.url,
            canonical_url=validated_url.canonical_url,
            feature_schema_version="features-v1",
        )
        await update_scan_completed(
            db=db,
            scan_id=scan.id,
            status="failed",
            error_code=e.code,
            error_message=str(e),
        )
        return create_scan_response(
            scan_id=scan.id,
            status="failed",
            error=str(e),
            error_code=e.code,
            created_at=scan.created_at,
        )

    scan = await create_scan(
        db=db,
        url=scan_request.url,
        canonical_url=validated_url.canonical_url,
        feature_schema_version="features-v1",
    )

    try:
        collector_response = await collect(validated_url, resolved_ip)
    except CollectorError as e:
        await update_scan_completed(
            db=db,
            scan_id=scan.id,
            status="failed",
            error_code=e.code,
            error_message=str(e),
        )
        return create_scan_response(
            scan_id=scan.id,
            status="failed",
            error=str(e),
            error_code=e.code,
            created_at=scan.created_at,
        )

    features = extract_features(collector_response)
    features_dict = (
        features.model_dump() if hasattr(features, "model_dump")
        else (features.to_dict() if hasattr(features, "to_dict") else dict(features))
    )

    rule_results = registry.run_all(features)

    all_findings = []
    for result in rule_results:
        if result.triggered:
            for finding in result.findings:
                all_findings.append(finding)

    risk_score = calculate_risk_score(all_findings)
    risk_tier = determine_risk_tier(risk_score)

    for finding in all_findings:
        await create_finding(
            db=db,
            scan_id=scan.id,
            rule_id=finding.rule_id,
            category=map_category(finding.category),
            severity=map_severity(finding.severity),
            title=finding.title,
            description=finding.description,
            evidence=(
                finding.evidence.model_dump()
                if hasattr(finding.evidence, "model_dump")
                else finding.evidence
            ),
            recommendation=finding.recommendation,
            source=map_source(finding.source),
            confidence=int(finding.confidence * 100),
        )

    await update_scan_completed(
        db=db,
        scan_id=scan.id,
        status="completed",
        risk_score=risk_score,
        risk_tier=risk_tier,
        score_source="fixed_baseline",
        features=features_dict,
        metadata={
            "status_code": collector_response.status_code,
            "content_type": collector_response.content_type,
            "response_time_ms": int(collector_response.response_time_ms),
            "redirect_count": collector_response.redirect_count,
            "final_url": collector_response.final_url,
            "content_length": len(collector_response.content),
        },
    )

    # Return the persisted representation so the create response is
    # identical to what a subsequent GET (and the exported report) shows.
    completed = await get_scan(db, scan.id)
    if completed is not None:
        completed.features = features_dict
        return _scan_to_response(completed)

    metadata = ScanMetadata(
        status_code=collector_response.status_code,
        content_type=collector_response.content_type,
        response_time_ms=collector_response.response_time_ms,
        redirect_count=collector_response.redirect_count,
        final_url=collector_response.final_url,
        content_length=len(collector_response.content),
    )

    return create_scan_response(
        scan_id=scan.id,
        status="completed",
        metadata=metadata,
        created_at=scan.created_at,
    )


@router.get("", response_model=ScanListResponse, status_code=status.HTTP_200_OK)
async def list_scans(
    limit: int = 50,
    offset: int = 0,
    status_filter: str | None = Query(None, alias="status"),
    tier_filter: str | None = Query(None, alias="tier"),
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> ScanListResponse:
    # Hard caps keep a single request from pulling unbounded rows.
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    scans = await get_scans(
        db,
        limit=limit,
        offset=offset,
        status=status_filter,
        tier=tier_filter,
        search=search,
    )
    total = await count_scans(
        db,
        status=status_filter,
        tier=tier_filter,
        search=search,
    )
    return ScanListResponse(
        scans=[_scan_to_response(scan) for scan in scans],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{scan_id}", response_model=ScanResponse, status_code=status.HTTP_200_OK)
async def get_scan_endpoint(
    scan_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ScanResponse:
    scan = await get_scan(db, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return _scan_to_response(scan)


@router.get(
    "/{scan_id}/export",
    response_model=ScanExportResponse,
    status_code=status.HTTP_200_OK,
)
async def export_scan_endpoint(
    scan_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    scan = await get_scan(db, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    export = ScanExportResponse(
        scan=_scan_to_response(scan),
        exported_at=datetime.now(UTC),
    )
    content = export.model_dump(mode="json")
    filename = f"tracera-scan-{scan.id}.json"
    return JSONResponse(
        content=content,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{scan_id}/findings", response_model=list[FindingResponse], status_code=status.HTTP_200_OK)
async def get_findings_endpoint(
    scan_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> list[FindingResponse]:
    scan = await get_scan(db, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    resp = _scan_to_response(scan)
    return resp.findings


@router.get("/{scan_id}/report", status_code=status.HTTP_200_OK)
async def get_report_endpoint(
    scan_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    scan = await get_scan(db, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    resp = _scan_to_response(scan)
    return {
        "scan_id": str(resp.scan_id),
        "url": resp.url,
        "canonical_url": resp.canonical_url,
        "status": resp.status,
        "risk_score": resp.risk_score,
        "risk_tier": resp.risk_tier,
        "score_source": resp.score_source,
        "feature_schema_version": resp.feature_schema_version,
        "ml_analysis": resp.ml_analysis,
        "scan_time": resp.created_at.isoformat() if resp.created_at else None,
        "completed_time": resp.completed_at.isoformat() if resp.completed_at else None,
        "finding_summary": {
            "total": len(resp.findings),
            "by_severity": {
                "critical": len([f for f in resp.findings if f.severity == "critical"]),
                "high": len([f for f in resp.findings if f.severity == "high"]),
                "medium": len([f for f in resp.findings if f.severity == "medium"]),
                "low": len([f for f in resp.findings if f.severity == "low"]),
                "info": len([f for f in resp.findings if f.severity == "info"]),
            },
            "by_category": {},
        },
        "findings": [
            {
                "id": str(f.id),
                "rule_id": f.rule_id,
                "category": f.category,
                "severity": f.severity,
                "title": f.title,
                "description": f.description,
                "evidence": f.evidence.model_dump() if hasattr(f.evidence, "model_dump") else (f.evidence or {}),
                "recommendation": f.recommendation,
                "source": f.source,
                "confidence": f.confidence,
            }
            for f in resp.findings
        ],
    }


def _scan_to_response(scan: Scan) -> ScanResponse:
    findings_response = []
    for f in scan.findings:
        evidence = FindingEvidence(**f.evidence_json) if f.evidence_json else FindingEvidence()
        findings_response.append(
            FindingResponse(
                id=f.id,
                rule_id=f.rule_id,
                category=f.category.value if hasattr(f.category, "value") else str(f.category),
                severity=f.severity.value if hasattr(f.severity, "value") else str(f.severity),
                title=f.title,
                description=f.description,
                evidence=evidence,
                recommendation=f.recommendation,
                source=f.source.value if hasattr(f.source, "value") else str(f.source),
                confidence=f.confidence / 100.0,
                created_at=f.created_at,
            )
        )

    metadata = None
    if scan.status == "completed" and scan.status_code is not None:
        metadata = ScanMetadata(
            status_code=scan.status_code,
            content_type=scan.content_type,
            response_time_ms=float(scan.response_time_ms or 0),
            redirect_count=scan.redirect_count or 0,
            final_url=scan.final_url or scan.canonical_url,
            content_length=scan.content_length or 0,
        )

    ml_analysis = None
    if getattr(scan, "features", None):
        try:
            from app.ml import analyze_scan_features, result_to_dict

            ml_analysis = result_to_dict(analyze_scan_features(scan.features))
        except Exception:
            ml_analysis = None

    return ScanResponse(
        scan_id=scan.id,
        status=scan.status.value if hasattr(scan.status, "value") else str(scan.status),
        url=scan.url,
        canonical_url=scan.canonical_url,
        feature_schema_version=getattr(scan, "feature_schema_version", None) or "features-v1",
        metadata=metadata,
        findings=findings_response,
        risk_score=scan.risk_score,
        risk_tier=scan.risk_tier.value if hasattr(scan.risk_tier, "value") else (str(scan.risk_tier) if scan.risk_tier else None),
        score_source=scan.score_source.value if hasattr(scan.score_source, "value") else (str(scan.score_source) if scan.score_source else None),
        error=scan.error_message,
        error_code=scan.error_code,
        created_at=scan.created_at,
        completed_at=scan.completed_at,
        ml_analysis=ml_analysis,
    )
