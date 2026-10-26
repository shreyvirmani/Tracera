from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ScanRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=2048)


class ScanMetadata(BaseModel):
    status_code: int
    content_type: str | None = None
    response_time_ms: float
    redirect_count: int
    final_url: str
    content_length: int


class FindingEvidence(BaseModel):
    model_config = {"extra": "allow"}


class FindingResponse(BaseModel):
    id: UUID
    rule_id: str
    category: str
    severity: str
    title: str
    description: str
    evidence: Any = None
    recommendation: str
    source: str
    confidence: float
    created_at: datetime


class ScanResponse(BaseModel):
    scan_id: UUID
    status: str
    url: str | None = None
    canonical_url: str | None = None
    feature_schema_version: str | None = "features-v1"
    metadata: ScanMetadata | None = None
    findings: list[FindingResponse] = []
    risk_score: int | None = None
    risk_tier: str | None = None
    score_source: str | None = None
    error: str | None = None
    error_code: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    ml_analysis: dict | None = None

    @property
    def id(self) -> UUID:
        return self.scan_id


class ScanListResponse(BaseModel):
    scans: list[ScanResponse]
    total: int
    limit: int
    offset: int


class ScanExportResponse(BaseModel):
    """Full machine-readable export of a scan, including its findings."""

    scan: ScanResponse
    exported_at: datetime
    generator: str = "Tracera 0.1.0"


def create_scan_response(
    scan_id: UUID,
    status: str,
    metadata: ScanMetadata | None = None,
    error: str | None = None,
    error_code: str | None = None,
    created_at: datetime | None = None,
    ml_analysis: dict | None = None,
) -> ScanResponse:
    return ScanResponse(
        scan_id=scan_id,
        status=status,
        metadata=metadata,
        error=error,
        error_code=error_code,
        created_at=created_at or datetime.now(UTC),
        ml_analysis=ml_analysis,
    )
