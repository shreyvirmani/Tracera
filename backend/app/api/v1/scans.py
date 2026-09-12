from uuid import uuid4

from fastapi import APIRouter, status

from app.api.v1.schemas import ScanMetadata, ScanRequest, ScanResponse, create_scan_response
from app.collector.collector import CollectorError, collect
from app.core.ssrf_guard import SSRFGuardError, check_ssrf
from app.core.url_validator import URLValidationError, canonicalize_url

router = APIRouter(prefix="/scans", tags=["scans"])


@router.post("", response_model=ScanResponse, status_code=status.HTTP_200_OK)
async def create_scan(request: ScanRequest) -> ScanResponse:
    scan_id = uuid4()

    try:
        validated_url = canonicalize_url(request.url)
    except URLValidationError as e:
        return create_scan_response(
            scan_id=scan_id,
            status="failed",
            error=str(e),
            error_code=e.code,
        )

    try:
        resolved_ip = check_ssrf(validated_url)
    except SSRFGuardError as e:
        return create_scan_response(
            scan_id=scan_id,
            status="failed",
            error=str(e),
            error_code=e.code,
        )

    try:
        collector_response = await collect(validated_url, resolved_ip)
    except CollectorError as e:
        return create_scan_response(
            scan_id=scan_id,
            status="failed",
            error=str(e),
            error_code=e.code,
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
        scan_id=scan_id,
        status="completed",
        metadata=metadata,
    )
