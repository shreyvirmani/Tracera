from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import (
    FindingEvidence,
    FindingResponse,
    ScanListResponse,
    ScanMetadata,
    ScanRequest,
    ScanResponse,
    create_scan_response,
)
from app.collector.collector import CollectorError, collect
from app.core.ssrf_guard import SSRFGuardError, check_ssrf
from app.core.url_validator import URLValidationError, canonicalize_url
from app.db.models import Scan
from app.db.repository import (
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

router = APIRouter(prefix="/scans", tags=["scans"])


@router.post("", response_model=ScanResponse, status_code=status.HTTP_200_OK)
async def create_scan_endpoint(
    request: ScanRequest, db: AsyncSession = Depends(get_db)
) -> ScanResponse:
    scan_id = uuid4()

    try:
        validated_url = canonicalize_url(request.url)
    except URLValidationError as e:
        await create_scan(
            db=db,
            url=request.url,
            canonical_url=request.url,
            feature_schema_version="features-v1",
        )
        return create_scan_response(
            scan_id=scan_id,
            status="failed",
            error=str(e),
            error_code=e.code,
        )

    try:
        resolved_ip = check_ssrf(validated_url)
    except SSRFGuardError as e:
        scan = await create_scan(
            db=db,
            url=request.url,
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
        )

    try:
        collector_response = await collect(validated_url, resolved_ip)
    except CollectorError as e:
        scan = await create_scan(
            db=db,
            url=request.url,
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
        )

    scan = await create_scan(
        db=db,
        url=request.url,
        canonical_url=validated_url.canonical_url,
        feature_schema_version="features-v1",
    )

    features = extract_features(collector_response)

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
    )

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
    )


@router.get("", response_model=ScanListResponse, status_code=status.HTTP_200_OK)
async def list_scans(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> ScanListResponse:
    scans = await get_scans(db, limit=limit, offset=offset)
    return ScanListResponse(
        scans=[_scan_to_response(scan) for scan in scans],
        total=len(scans),
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


def _scan_to_response(scan: Scan) -> ScanResponse:
    findings_response = []
    for f in scan.findings:
        evidence = FindingEvidence(**f.evidence_json) if f.evidence_json else FindingEvidence()
        findings_response.append(
            FindingResponse(
                id=f.id,
                rule_id=f.rule_id,
                category=f.category.value,
                severity=f.severity.value,
                title=f.title,
                description=f.description,
                evidence=evidence,
                recommendation=f.recommendation,
                source=f.source.value,
                confidence=f.confidence / 100.0,
                created_at=f.created_at,
            )
        )

    metadata = None
    if scan.status == "completed" and scan.risk_score is not None:
        metadata = ScanMetadata(
            status_code=200,
            content_type="text/html",
            response_time_ms=0,
            redirect_count=0,
            final_url=scan.canonical_url,
            content_length=0,
        )

    return ScanResponse(
        scan_id=scan.id,
        status=scan.status,
        metadata=metadata,
        findings=findings_response,
        risk_score=scan.risk_score,
        risk_tier=scan.risk_tier.value if scan.risk_tier else None,
        score_source=scan.score_source.value if scan.score_source else None,
        error=scan.error_message,
        error_code=scan.error_code,
        created_at=scan.created_at,
        completed_at=scan.completed_at,
    )
