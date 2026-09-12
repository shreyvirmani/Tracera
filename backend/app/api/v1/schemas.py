from uuid import UUID

from pydantic import BaseModel, Field


class ScanRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=2048)


class ScanMetadata(BaseModel):
    status_code: int
    content_type: str | None
    response_time_ms: float
    redirect_count: int
    final_url: str
    content_length: int


class ScanResponse(BaseModel):
    scan_id: UUID
    status: str
    metadata: ScanMetadata | None = None
    error: str | None = None
    error_code: str | None = None


def create_scan_response(
    scan_id: UUID,
    status: str,
    metadata: ScanMetadata | None = None,
    error: str | None = None,
    error_code: str | None = None,
) -> ScanResponse:
    return ScanResponse(
        scan_id=scan_id,
        status=status,
        metadata=metadata,
        error=error,
        error_code=error_code,
    )
