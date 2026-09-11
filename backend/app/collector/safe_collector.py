import httpx
import ssl
import time
from typing import Optional
from dataclasses import dataclass

from app.core.config import settings
from app.core.url_validator import ValidatedURL, validate_redirect_url, URLValidationError


@dataclass
class CollectorResponse:
    status_code: int
    headers: dict[str, str]
    content: bytes
    url: str
    response_time_ms: float
    redirect_count: int
    tls_info: Optional[dict] = None
    error: Optional[str] = None


class CollectorError(Exception):
    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code
        super().__init__(message)


async def fetch(url: ValidatedURL) -> CollectorResponse:
    start_time = time.perf_counter()
    redirect_count = 0
    current_url = url.canonical_url
    current_validated = url

    headers = {
        "User-Agent": settings.collector_user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "close",
    }

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = True
    ssl_context.verify_mode = ssl.CERT_REQUIRED

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(settings.collector_timeout_seconds),
        follow_redirects=False,
        verify=ssl_context,
        headers=headers,
    ) as client:
        while redirect_count <= settings.collector_max_redirects:
            try:
                response = await client.get(current_url)
            except httpx.TimeoutException:
                raise CollectorError("Request timeout", "TIMEOUT")
            except httpx.TooManyRedirects:
                raise CollectorError("Too many redirects", "TOO_MANY_REDIRECTS")
            except httpx.RequestError as e:
                raise CollectorError(f"Request failed: {type(e).__name__}", "REQUEST_FAILED")

            response_time_ms = (time.perf_counter() - start_time) * 1000

            response_headers = dict(response.headers)

            if len(response.content) > settings.collector_max_response_size:
                raise CollectorError(
                    f"Response size exceeds limit: {len(response.content)} > {settings.collector_max_response_size}",
                    "RESPONSE_TOO_LARGE",
                )

            if response.is_redirect or response.status_code in (301, 302, 303, 307, 308):
                redirect_count += 1
                if redirect_count > settings.collector_max_redirects:
                    raise CollectorError("Redirect limit exceeded", "REDIRECT_LIMIT_EXCEEDED")

                location = response.headers.get("location")
                if not location:
                    raise CollectorError("Redirect without Location header", "MISSING_LOCATION")

                try:
                    current_validated = validate_redirect_url(location, current_validated)
                    current_url = current_validated.canonical_url
                except URLValidationError as e:
                    raise CollectorError(f"Redirect validation failed: {e.message}", f"REDIRECT_{e.code}")

                continue

            tls_info = None
            if current_url.startswith("https://"):
                try:
                    tls_info = await _get_tls_info(current_validated.hostname)
                except Exception:
                    tls_info = None

            return CollectorResponse(
                status_code=response.status_code,
                headers=response_headers,
                content=response.content,
                url=current_url,
                response_time_ms=response_time_ms,
                redirect_count=redirect_count,
                tls_info=tls_info,
            )

    raise CollectorError("Max redirects exceeded", "MAX_REDIRECTS")


async def _get_tls_info(hostname: str) -> Optional[dict]:
    import socket
    import ssl
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        context = ssl.create_default_context()

        def get_cert():
            with socket.create_connection((hostname, 443), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    return ssock.getpeercert()

        cert = await loop.run_in_executor(None, get_cert)
        if not cert:
            return None

        return {
            "version": cert.get("version"),
            "subject": dict(x[0] for x in cert.get("subject", [])),
            "issuer": dict(x[0] for x in cert.get("issuer", [])),
            "not_before": cert.get("notBefore"),
            "not_after": cert.get("notAfter"),
            "serial_number": cert.get("serialNumber"),
            "subject_alt_names": cert.get("subjectAltName", []),
        }
    except Exception:
        return None