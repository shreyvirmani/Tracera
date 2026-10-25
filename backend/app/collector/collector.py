import time
from dataclasses import dataclass
from urllib.parse import urljoin

import httpx

from app.core.config import settings
from app.core.ssrf_guard import ResolvedIP, SSRFGuardError, validate_redirect_target
from app.core.url_validator import ValidatedURL


@dataclass(frozen=True)
class CollectorResponse:
    status_code: int
    headers: dict[str, str]
    content: bytes
    content_type: str | None
    response_time_ms: float
    redirect_count: int
    final_url: str
    tls_info: dict | None = None


class CollectorError(Exception):
    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


USER_AGENT = "Tracera/0.1.0 (+https://tracera.dev)"


def _pinned_request_url(url: ValidatedURL, resolved_ip: ResolvedIP) -> str:
    """Build a request URL that connects to the validated IP directly.

    The Host header and TLS SNI still carry the original hostname, so virtual
    hosting and certificate validation keep working while DNS is bypassed
    entirely. This closes the DNS-rebinding window between validation and
    connection: the socket is opened to exactly the address that was screened.
    """
    host_for_url = resolved_ip.ip
    if resolved_ip.version == 6:
        host_for_url = f"[{resolved_ip.ip}]"
    port_part = f":{url.port}" if url.port not in (80, 443) else ""
    return f"{url.scheme}://{host_for_url}{port_part}{url.path}" + (
        f"?{url.query}" if url.query else ""
    )


async def collect(url: ValidatedURL, resolved_ip: ResolvedIP) -> CollectorResponse:
    timeout = httpx.Timeout(
        settings.SCANNER_TIMEOUT_SECONDS,
        connect=settings.SCANNER_CONNECT_TIMEOUT_SECONDS,
    )
    client = httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=False,
        headers={"User-Agent": USER_AGENT},
        limits=httpx.Limits(max_connections=1, max_keepalive_connections=0),
    )

    start_time = time.perf_counter()

    try:
        current: ValidatedURL = url
        current_ip: ResolvedIP = resolved_ip
        redirect_count = 0
        total_size = 0

        while True:
            elapsed = time.perf_counter() - start_time
            if elapsed > settings.SCANNER_TOTAL_TIME_SECONDS:
                raise CollectorError("Scan exceeded total time budget", "TOTAL_TIME_EXCEEDED")

            request_url = _pinned_request_url(current, current_ip)
            request = client.build_request(
                "GET",
                request_url,
                headers={"Host": current.host},
                extensions={"sni_hostname": current.host},
            )

            try:
                response = await client.send(request, stream=True)
            except SSRFGuardError:
                raise
            except httpx.TimeoutException:
                raise CollectorError("Request timed out", "TIMEOUT") from None
            except httpx.RequestError as e:
                raise CollectorError(f"Request failed: {e}", "REQUEST_FAILED") from None

            # Redirect handling: every destination is revalidated (scheme,
            # port policy, DNS resolution, IP screening) before the next hop.
            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get("location")
                if location:
                    await response.aclose()
                    redirect_count += 1
                    if redirect_count > settings.SCANNER_MAX_REDIRECTS:
                        raise CollectorError("Too many redirects", "TOO_MANY_REDIRECTS")
                    try:
                        next_url = urljoin(current.canonical_url, location)
                        current, current_ip = validate_redirect_target(next_url)
                    except SSRFGuardError as e:
                        raise CollectorError(
                            f"Redirect target blocked: {e}", "REDIRECT_TARGET_BLOCKED"
                        ) from e
                    continue
                # 3xx without Location: fall through and record it as the
                # final response rather than failing the scan.

            try:
                content_chunks = []
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    total_size += len(chunk)
                    if total_size > settings.SCANNER_MAX_RESPONSE_BYTES:
                        raise CollectorError(
                            f"Response size exceeds limit of "
                            f"{settings.SCANNER_MAX_RESPONSE_BYTES} bytes",
                            "RESPONSE_TOO_LARGE",
                        )
                    content_chunks.append(chunk)
            except CollectorError:
                raise
            except httpx.DecodingError as e:
                raise CollectorError(
                    f"Malformed response body: {e}", "MALFORMED_RESPONSE"
                ) from None
            except httpx.RequestError as e:
                raise CollectorError(f"Request failed: {e}", "REQUEST_FAILED") from None
            finally:
                await response.aclose()

            content = b"".join(content_chunks)
            response_time_ms = (time.perf_counter() - start_time) * 1000
            headers = dict(response.headers)
            content_type = headers.get("content-type")

            return CollectorResponse(
                status_code=response.status_code,
                headers=headers,
                content=content,
                content_type=content_type,
                response_time_ms=response_time_ms,
                redirect_count=redirect_count,
                final_url=current.canonical_url,
            )
    finally:
        await client.aclose()
