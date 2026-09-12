from app.collector.collector import CollectorResponse
from app.features.schema import HTTPFeatures


def extract_http_features(response: CollectorResponse) -> HTTPFeatures:
    headers = {k.lower(): v for k, v in response.headers.items()}

    content_length = headers.get("content-length")
    if content_length:
        try:
            response_size = int(content_length)
        except ValueError:
            response_size = len(response.content)
    else:
        response_size = len(response.content)

    https_enabled = response.final_url.startswith("https://")

    return HTTPFeatures(
        status_code=response.status_code,
        response_size_bytes=response_size,
        response_time_ms=response.response_time_ms,
        content_type=response.content_type,
        redirect_count=response.redirect_count,
        https_enabled=https_enabled,
        server_header=headers.get("server"),
        x_powered_by=headers.get("x-powered-by"),
    )
