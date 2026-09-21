import numpy as np

from app.features.schema import FeatureVector

FEATURE_ORDER = [
    # HTTP features
    "http.status_code",
    "http.response_size_bytes",
    "http.response_time_ms",
    "http.redirect_count",
    "http.https_enabled",
    # Security headers (1 = present, 0 = absent)
    "security_headers.hsts",
    "security_headers.csp",
    "security_headers.x_content_type_options",
    "security_headers.x_frame_options",
    "security_headers.referrer_policy",
    "security_headers.permissions_policy",
    "security_headers.cross_origin_embedder_policy",
    "security_headers.cross_origin_opener_policy",
    "security_headers.cross_origin_resource_policy",
    "security_headers.access_control_allow_origin",
    "security_headers.access_control_allow_credentials",
    # Cookie features
    "cookies.total_cookies",
    "cookies.secure_cookies",
    "cookies.httponly_cookies",
    "cookies.samesite_cookies",
    "cookies.session_cookies",
    "cookies.persistent_cookies",
    "cookies.third_party_indicators",
    # TLS features
    "tls.cert_expiry_days",
    "tls.cert_expired",
    "tls.tls_version",
    "tls.cipher_suite",
    # HTML features
    "html.html_size_bytes",
    "html.script_count",
    "html.stylesheet_count",
    "html.image_count",
    "html.iframe_count",
    "html.form_count",
    "html.external_domain_count",
    "html.mixed_content_count",
    "html.has_password_field",
    "html.has_file_upload",
    # Technology features
    "technology.server_header_present",
    "technology.x_powered_by_present",
]


def feature_vector_to_array(features: FeatureVector) -> np.ndarray:
    """Convert FeatureVector to flat numpy array for ML models."""
    arr = []

    # HTTP
    arr.append(features.http.status_code)
    arr.append(features.http.response_size_bytes)
    arr.append(features.http.response_time_ms)
    arr.append(features.http.redirect_count)
    arr.append(1.0 if features.http.https_enabled else 0.0)

    # Security headers
    for header in [
        "hsts",
        "csp",
        "x_content_type_options",
        "x_frame_options",
        "referrer_policy",
        "permissions_policy",
        "cross_origin_embedder_policy",
        "cross_origin_opener_policy",
        "cross_origin_resource_policy",
        "access_control_allow_origin",
        "access_control_allow_credentials",
    ]:
        val = getattr(features.security_headers, header)
        arr.append(1.0 if val else 0.0)

    # Cookies
    arr.append(features.cookies.total_cookies)
    arr.append(features.cookies.secure_cookies)
    arr.append(features.cookies.httponly_cookies)
    arr.append(features.cookies.samesite_cookies)
    arr.append(features.cookies.session_cookies)
    arr.append(features.cookies.persistent_cookies)
    arr.append(features.cookies.third_party_indicators)

    # TLS
    arr.append(features.tls.cert_expiry_days or 0.0)
    arr.append(1.0 if features.tls.cert_expired else 0.0)
    # TLS version: map to numeric
    tls_version_map = {"TLSv1.3": 4.0, "TLSv1.2": 3.0, "TLSv1.1": 2.0, "TLSv1.0": 1.0}
    arr.append(tls_version_map.get(features.tls.tls_version or "", 0.0))
    # Cipher suite: 1 if present
    arr.append(1.0 if features.tls.cipher_suite else 0.0)

    # HTML
    arr.append(features.html.html_size_bytes)
    arr.append(features.html.script_count)
    arr.append(features.html.stylesheet_count)
    arr.append(features.html.image_count)
    arr.append(features.html.iframe_count)
    arr.append(features.html.form_count)
    arr.append(features.html.external_domain_count)
    arr.append(features.html.mixed_content_count)
    arr.append(1.0 if features.html.has_password_field else 0.0)
    arr.append(1.0 if features.html.has_file_upload else 0.0)

    # Technology
    arr.append(1.0 if features.technology.server_header_present else 0.0)
    arr.append(1.0 if features.technology.x_powered_by_present else 0.0)

    return np.array(arr, dtype=np.float32)


def feature_vectors_to_matrix(features_list: list[FeatureVector]) -> np.ndarray:
    """Convert list of FeatureVectors to 2D numpy array."""
    return np.vstack([feature_vector_to_array(f) for f in features_list])


def get_feature_names() -> list[str]:
    return FEATURE_ORDER.copy()


def tier_to_label(tier: str) -> int:
    mapping = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    return mapping.get(tier, 0)


def label_to_tier(idx: int) -> str:
    tiers = ["low", "medium", "high", "critical"]
    return tiers[idx] if 0 <= idx < 4 else "low"
