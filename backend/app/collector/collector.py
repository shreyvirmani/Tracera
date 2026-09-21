import time
from dataclasses import dataclass

import httpx

from app.core.ssrf_guard import ResolvedIP
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


DEFAULT_TIMEOUT = 10.0
MAX_RESPONSE_SIZE = 10 * 1024 * 1024
MAX_REDIRECTS = 5
USER_AGENT = "Tracera/0.1.0 (+https://tracera.dev)"


class SafeRedirectMiddleware:
    def __init__(self, max_redirects: int = MAX_REDIRECTS):
        self.max_redirects = max_redirects
        self.redirect_count = 0

    def __call__(self, request: httpx.Request) -> httpx.Request:
        return request


async def collect(url: ValidatedURL, resolved_ip: ResolvedIP) -> CollectorResponse:
    client = httpx.AsyncClient(
        timeout=httpx.Timeout(DEFAULT_TIMEOUT, connect=5.0),
        follow_redirects=False,
        headers={"User-Agent": USER_AGENT},
        limits=httpx.Limits(max_connections=1, max_keepalive_connections=0),
    )

    try:
        response = await _safe_request(client, url.canonical_url, resolved_ip)
        return response
    except httpx.TimeoutException:
        raise CollectorError("Request timed out", "TIMEOUT") from None
    except httpx.TooManyRedirects:
        raise CollectorError("Too many redirects", "TOO_MANY_REDIRECTS") from None
    except httpx.RequestError as e:
        raise CollectorError(f"Request failed: {e}", "REQUEST_FAILED") from None
    finally:
        await client.aclose()


async def _safe_request(
    client: httpx.AsyncClient, url: str, resolved_ip: ResolvedIP
) -> CollectorResponse:
    redirect_count = 0
    current_url = url
    start_time = time.perf_counter()
    total_size = 0

    while redirect_count <= MAX_REDIRECTS:
        request = client.build_request("GET", current_url)
        response = await client.send(request, stream=True)

        if response.is_redirect or response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get("location")
            if not location:
                break
            redirect_count += 1
            if redirect_count > MAX_REDIRECTS:
                await response.aclose()
                raise CollectorError("Too many redirects", "TOO_MANY_REDIRECTS")

            from urllib.parse import urljoin

            current_url = urljoin(str(response.url), location)
            await response.aclose()
            continue

        content_chunks = []
        async for chunk in response.aiter_bytes(chunk_size=8192):
            total_size += len(chunk)
            if total_size > MAX_RESPONSE_SIZE:
                await response.aclose()
                raise CollectorError(
                    f"Response size exceeds limit of {MAX_RESPONSE_SIZE} bytes",
                    "RESPONSE_TOO_LARGE",
                )
            content_chunks.append(chunk)

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
            final_url=str(response.url),
        )

    raise CollectorError("Max redirects exceeded", "TOO_MANY_REDIRECTS")
