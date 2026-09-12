from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    DetectionSource,
    Finding,
    FindingCategory,
    FindingSeverity,
    Scan,
    ScanStatus,
)


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
) -> Scan | None:
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()
    if not scan:
        return None

    scan.status = status
    scan.completed_at = __import__("datetime").datetime.utcnow()
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


async def get_scans(db: AsyncSession, limit: int = 50, offset: int = 0) -> list[Scan]:
    result = await db.execute(
        select(Scan).order_by(Scan.created_at.desc()).limit(limit).offset(offset)
    )
    return list(result.scalars().all())
