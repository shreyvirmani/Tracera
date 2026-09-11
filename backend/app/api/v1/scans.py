from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, HttpUrl
from typing import Optional, List
import uuid
from datetime import datetime

from app.core.url_validator import validate_url, URLValidationError
from app.collector.safe_collector import fetch, CollectorError
from app.features.extractor import extract_features
from app.rules.engine import run_rules
from app.scoring.engine import score_findings
from app.db.session import get_db
from app.db.models import Scan, Finding, ScanStatus, ScoreSource, RiskTier, FindingSeverity, FindingCategory, FindingSource

router = APIRouter()


class ScanRequest(BaseModel):
    url: HttpUrl


class ScanResponse(BaseModel):
    scan_id: uuid.UUID
    status: str


class FindingResponse(BaseModel):
    id: uuid.UUID
    rule_id: str
    category: str
    severity: str
    title: str
    description: str
    evidence: dict
    recommendation: str
    source: str
    confidence: float


class ScanDetailResponse(BaseModel):
    id: uuid.UUID
    url: str
    canonical_url: str
    status: str
    feature_schema_version: str
    risk_score: Optional[int] = None
    risk_tier: Optional[str] = None
    score_source: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    findings: List[FindingResponse] = []


@router.post("/scans", response_model=ScanResponse, status_code=202)
async def create_scan(request: ScanRequest, db: AsyncSession = Depends(get_db)):
    url_str = str(request.url)

    try:
        validated = await validate_url(url_str)
    except URLValidationError as e:
        raise HTTPException(status_code=400, detail={"code": e.code, "message": e.message})

    scan = Scan(
        url=url_str,
        canonical_url=validated.canonical_url,
        status=ScanStatus.PENDING,
        feature_schema_version="v1",
    )
    db.add(scan)
    await db.flush()

    try:
        response = await fetch(validated)
    except CollectorError as e:
        scan.status = ScanStatus.FAILED
        scan.error_code = e.code
        scan.error_message = e.message
        scan.completed_at = datetime.utcnow()
        await db.commit()
        raise HTTPException(status_code=502, detail={"code": e.code, "message": e.message})

    features = extract_features(response, validated)
    findings = run_rules(features)
    scoring = score_findings(findings)

    scan.status = ScanStatus.COMPLETED
    scan.feature_schema_version = features.feature_schema_version
    scan.risk_score = scoring["risk_score"]
    scan.risk_tier = RiskTier(scoring["risk_tier"])
    scan.score_source = ScoreSource(scoring["score_source"])
    scan.completed_at = datetime.utcnow()
    scan.features = features.to_dict()

    for f in findings:
        finding = Finding(
            scan_id=scan.id,
            rule_id=f.rule_id,
            category=FindingCategory(f.category),
            severity=FindingSeverity(f.severity),
            title=f.title,
            description=f.description,
            evidence_json=f.evidence,
            recommendation=f.recommendation,
            source=FindingSource(f.source),
            confidence=int(f.confidence * 100),
        )
        db.add(finding)

    await db.commit()
    await db.refresh(scan)

    return ScanResponse(scan_id=scan.id, status=scan.status.value)


@router.get("/scans/{scan_id}", response_model=ScanDetailResponse)
async def get_scan(scan_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    stmt = select(Scan).options(selectinload(Scan.findings)).where(Scan.id == scan_id)
    result = await db.execute(stmt)
    scan = result.scalar_one_or_none()

    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    findings_resp = [
        FindingResponse(
            id=f.id,
            rule_id=f.rule_id,
            category=f.category.value,
            severity=f.severity.value,
            title=f.title,
            description=f.description,
            evidence=f.evidence_json,
            recommendation=f.recommendation,
            source=f.source.value,
            confidence=f.confidence / 100.0,
        )
        for f in scan.findings
    ]

    return ScanDetailResponse(
        id=scan.id,
        url=scan.url,
        canonical_url=scan.canonical_url,
        status=scan.status.value,
        feature_schema_version=scan.feature_schema_version,
        risk_score=scan.risk_score,
        risk_tier=scan.risk_tier.value if scan.risk_tier else None,
        score_source=scan.score_source.value if scan.score_source else None,
        created_at=scan.created_at,
        completed_at=scan.completed_at,
        error_code=scan.error_code,
        error_message=scan.error_message,
        findings=findings_resp,
    )


@router.get("/scans/{scan_id}/findings", response_model=List[FindingResponse])
async def get_findings(scan_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select

    stmt = select(Finding).where(Finding.scan_id == scan_id)
    result = await db.execute(stmt)
    findings = result.scalars().all()

    return [
        FindingResponse(
            id=f.id,
            rule_id=f.rule_id,
            category=f.category.value,
            severity=f.severity.value,
            title=f.title,
            description=f.description,
            evidence=f.evidence_json,
            recommendation=f.recommendation,
            source=f.source.value,
            confidence=f.confidence / 100.0,
        )
        for f in findings
    ]


@router.get("/scans/{scan_id}/report")
async def get_report(scan_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    scan_detail = await get_scan(scan_id, db)
    return {
        "scan_id": str(scan_detail.id),
        "url": scan_detail.url,
        "canonical_url": scan_detail.canonical_url,
        "risk_score": scan_detail.risk_score,
        "risk_tier": scan_detail.risk_tier,
        "score_source": scan_detail.score_source,
        "feature_schema_version": scan_detail.feature_schema_version,
        "scan_time": scan_detail.created_at.isoformat(),
        "completed_time": scan_detail.completed_at.isoformat() if scan_detail.completed_at else None,
        "finding_summary": {
            "total": len(scan_detail.findings),
            "by_severity": {
                "critical": len([f for f in scan_detail.findings if f.severity == "critical"]),
                "high": len([f for f in scan_detail.findings if f.severity == "high"]),
                "medium": len([f for f in scan_detail.findings if f.severity == "medium"]),
                "low": len([f for f in scan_detail.findings if f.severity == "low"]),
                "info": len([f for f in scan_detail.findings if f.severity == "info"]),
            },
            "by_category": {},
        },
        "findings": [
            {
                "rule_id": f.rule_id,
                "category": f.category,
                "severity": f.severity,
                "title": f.title,
                "description": f.description,
                "evidence": f.evidence,
                "recommendation": f.recommendation,
                "source": f.source,
            }
            for f in scan_detail.findings
        ],
    }