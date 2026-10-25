from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    DetectionSource,
    Finding,
    FindingCategory,
    FindingSeverity,
    RiskTier,
    Scan,
    ScanStatus,
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


async def create_scan(
    db: AsyncSession,
    url: str,
    canonical_url: str,
    feature_schema_version: str,
) -> Scan:
    scan = Scan(
        url=url,
        canonical_url=canonical_url,
        status=ScanStatus.PENDING,
        feature_schema_version=feature_schema_version,
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)
    return scan


async def update_scan_completed(
    db: AsyncSession,
    scan_id: UUID,
    status: ScanStatus,
    risk_score: int | None = None,
    risk_tier: str | None = None,
    score_source: str | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
    metadata: dict | None = None,
) -> Scan | None:
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()
    if not scan:
        return None

    scan.status = status
    scan.completed_at = _utcnow()
    if risk_score is not None:
        scan.risk_score = risk_score
    if risk_tier is not None:
        scan.risk_tier = risk_tier
    if score_source is not None:
        scan.score_source = score_source
    if error_code is not None:
        scan.error_code = error_code
    if error_message is not None:
        scan.error_message = error_message
    if metadata is not None:
        for key, value in metadata.items():
            if hasattr(scan, key):
                setattr(scan, key, value)

    await db.commit()
    await db.refresh(scan)
    return scan


async def create_finding(
    db: AsyncSession,
    scan_id: UUID,
    rule_id: str,
    category: FindingCategory,
    severity: FindingSeverity,
    title: str,
    description: str,
    evidence: dict,
    recommendation: str,
    source: DetectionSource = DetectionSource.RULE_ENGINE,
    confidence: int = 100,
) -> Finding:
    finding = Finding(
        scan_id=scan_id,
        rule_id=rule_id,
        category=category,
        severity=severity,
        title=title,
        description=description,
        evidence_json=evidence,
        recommendation=recommendation,
        source=source,
        confidence=confidence,
    )
    db.add(finding)
    await db.commit()
    await db.refresh(finding)
    return finding


async def get_scan(db: AsyncSession, scan_id: UUID) -> Scan | None:
    result = await db.execute(
        select(Scan).options(selectinload(Scan.findings)).where(Scan.id == scan_id)
    )
    return result.scalar_one_or_none()


async def get_scans(
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
    tier: str | None = None,
    search: str | None = None,
) -> list[Scan]:
    query = select(Scan).options(selectinload(Scan.findings))

    if status:
        try:
            query = query.where(Scan.status == ScanStatus(status.lower()))
        except ValueError:
            return []
    if tier:
        try:
            query = query.where(Scan.risk_tier == RiskTier(tier.lower()))
        except ValueError:
            return []
    if search:
        pattern = f"%{search}%"
        query = query.where(or_(Scan.url.ilike(pattern), Scan.canonical_url.ilike(pattern)))

    query = query.order_by(Scan.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all())


async def count_scans(
    db: AsyncSession,
    status: str | None = None,
    tier: str | None = None,
    search: str | None = None,
) -> int:
    query = select(func.count()).select_from(Scan)

    if status:
        try:
            query = query.where(Scan.status == ScanStatus(status.lower()))
        except ValueError:
            return 0
    if tier:
        try:
            query = query.where(Scan.risk_tier == RiskTier(tier.lower()))
        except ValueError:
            return 0
    if search:
        pattern = f"%{search}%"
        query = query.where(or_(Scan.url.ilike(pattern), Scan.canonical_url.ilike(pattern)))

    result = await db.execute(query)
    return int(result.scalar_one())
