from app.collector.collector import CollectorResponse
from app.features.schema import SecurityHeaderFeatures

SECURITY_HEADERS = {
    "strict-transport-security": "hsts",
    "content-security-policy": "csp",
    "x-content-type-options": "x_content_type_options",
    "x-frame-options": "x_frame_options",
    "referrer-policy": "referrer_policy",
    "permissions-policy": "permissions_policy",
    "cross-origin-embedder-policy": "cross_origin_embedder_policy",
    "cross-origin-opener-policy": "cross_origin_opener_policy",
    "cross-origin-resource-policy": "cross_origin_resource_policy",
}


def extract_security_headers(response: CollectorResponse) -> SecurityHeaderFeatures:
    headers = {k.lower(): v for k, v in response.headers.items()}

    extracted = {}
    for header_name, field_name in SECURITY_HEADERS.items():
        extracted[field_name] = headers.get(header_name)

    return SecurityHeaderFeatures(**extracted)
