"""
Tracera ML Feature Schema v1

This module defines the ML feature vector contract (MLFeaturesV1) and the
separate metadata record (DatasetMetadata). The ML feature vector contains
ONLY stable, low-cardinality, numerical/binary features suitable for model
input. All high-cardinality, raw, or provenance fields are kept in metadata.

The schema is versioned. Any breaking change requires a version bump.

Feature extraction adapters (for live scanner, Common Crawl WAT, etc.) produce
MLFeaturesV1 instances from their respective data sources.
"""

from dataclasses import dataclass, asdict, field
from typing import Optional
import numpy as np


ML_FEATURE_SCHEMA_VERSION = "v1"


@dataclass
class MLFeaturesV1:
    """
    ML Feature Vector v1 — 17 features total.

    All features are numerical (int/float) or binary (0/1). No strings,
    no high-cardinality categoricals, no raw header values.

    Feature groups:
    - HTTP (3): status_code, is_html, https_enabled
    - Security Headers (5): hsts_present, csp_present, x_content_type_options_present,
                            x_frame_options_present, referrer_policy_present,
                            permissions_policy_present
    - Cookies (6): cookie_count, cookie_secure_ratio, cookie_httponly_ratio,
                   cookie_samesite_strict_ratio, cookie_samesite_lax_ratio,
                   cookie_samesite_none_ratio
    - Tech Disclosure (2): server_header_present, x_powered_by_present
    """

    feature_schema_version: str = ML_FEATURE_SCHEMA_VERSION

    # HTTP (3)
    status_code: int = 0
    is_html: int = 0          # 1 if text/html, 0 otherwise
    https_enabled: int = 0    # 1 if HTTPS, 0 if HTTP

    # Security Headers (6) - all binary 0/1
    hsts_present: int = 0
    csp_present: int = 0
    x_content_type_options_present: int = 0
    x_frame_options_present: int = 0
    referrer_policy_present: int = 0
    permissions_policy_present: int = 0

    # Cookies (6)
    cookie_count: int = 0
    cookie_secure_ratio: float = 0.0
    cookie_httponly_ratio: float = 0.0
    cookie_samesite_strict_ratio: float = 0.0
    cookie_samesite_lax_ratio: float = 0.0
    cookie_samesite_none_ratio: float = 0.0

    # Tech Disclosure (2) - binary presence only, no raw values
    server_header_present: int = 0
    x_powered_by_present: int = 0

    def to_array(self) -> np.ndarray:
        """Convert to numpy array in fixed feature order for model input."""
        return np.array([
            self.status_code,
            self.is_html,
            self.https_enabled,
            self.hsts_present,
            self.csp_present,
            self.x_content_type_options_present,
            self.x_frame_options_present,
            self.referrer_policy_present,
            self.permissions_policy_present,
            self.cookie_count,
            self.cookie_secure_ratio,
            self.cookie_httponly_ratio,
            self.cookie_samesite_strict_ratio,
            self.cookie_samesite_lax_ratio,
            self.cookie_samesite_none_ratio,
            self.server_header_present,
            self.x_powered_by_present,
        ], dtype=np.float32)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def feature_names(cls) -> list[str]:
        """Return feature names in the same order as to_array()."""
        return [
            "status_code",
            "is_html",
            "https_enabled",
            "hsts_present",
            "csp_present",
            "x_content_type_options_present",
            "x_frame_options_present",
            "referrer_policy_present",
            "permissions_policy_present",
            "cookie_count",
            "cookie_secure_ratio",
            "cookie_httponly_ratio",
            "cookie_samesite_strict_ratio",
            "cookie_samesite_lax_ratio",
            "cookie_samesite_none_ratio",
            "server_header_present",
            "x_powered_by_present",
        ]

    @classmethod
    def feature_spec(cls) -> dict:
        """Return detailed specification for each feature."""
        return {
            "status_code": {
                "type": "int",
                "range": "[100, 599]",
                "meaning": "HTTP response status code",
                "source": "HTTP response",
                "missing_possible": False,
                "used_by_model": True,
            },
            "is_html": {
                "type": "binary",
                "range": "{0, 1}",
                "meaning": "1 if Content-Type indicates text/html, 0 otherwise",
                "source": "Content-Type header",
                "missing_possible": True,  # header may be missing
                "used_by_model": True,
            },
            "https_enabled": {
                "type": "binary",
                "range": "{0, 1}",
                "meaning": "1 if URL scheme is https, 0 if http",
                "source": "URL scheme",
                "missing_possible": False,
                "used_by_model": True,
            },
            "hsts_present": {
                "type": "binary",
                "range": "{0, 1}",
                "meaning": "1 if Strict-Transport-Security header present",
                "source": "Response headers",
                "missing_possible": False,  # absent = 0
                "used_by_model": True,
            },
            "csp_present": {
                "type": "binary",
                "range": "{0, 1}",
                "meaning": "1 if Content-Security-Policy header present",
                "source": "Response headers",
                "missing_possible": False,
                "used_by_model": True,
            },
            "x_content_type_options_present": {
                "type": "binary",
                "range": "{0, 1}",
                "meaning": "1 if X-Content-Type-Options: nosniff present",
                "source": "Response headers",
                "missing_possible": False,
                "used_by_model": True,
            },
            "x_frame_options_present": {
                "type": "binary",
                "range": "{0, 1}",
                "meaning": "1 if X-Frame-Options header present",
                "source": "Response headers",
                "missing_possible": False,
                "used_by_model": True,
            },
            "referrer_policy_present": {
                "type": "binary",
                "range": "{0, 1}",
                "meaning": "1 if Referrer-Policy header present",
                "source": "Response headers",
                "missing_possible": False,
                "used_by_model": True,
            },
            "permissions_policy_present": {
                "type": "binary",
                "range": "{0, 1}",
                "meaning": "1 if Permissions-Policy header present",
                "source": "Response headers",
                "missing_possible": False,
                "used_by_model": True,
            },
            "cookie_count": {
                "type": "int",
                "range": "[0, inf)",
                "meaning": "Number of Set-Cookie headers observed",
                "source": "Set-Cookie header",
                "missing_possible": False,  # 0 if no header
                "used_by_model": True,
            },
            "cookie_secure_ratio": {
                "type": "float",
                "range": "[0.0, 1.0]",
                "meaning": "Fraction of cookies with Secure flag. 0.0 if cookie_count=0 (indistinguishable from 'cookies exist but none secure').",
                "source": "Set-Cookie header parsing",
                "missing_possible": False,  # 0.0 default
                "used_by_model": True,
                "limitation": "Cannot distinguish 'no cookies' from 'cookies but none secure' — both yield 0.0",
            },
            "cookie_httponly_ratio": {
                "type": "float",
                "range": "[0.0, 1.0]",
                "meaning": "Fraction of cookies with HttpOnly flag",
                "source": "Set-Cookie header parsing",
                "missing_possible": False,
                "used_by_model": True,
                "limitation": "Same limitation as cookie_secure_ratio",
            },
            "cookie_samesite_strict_ratio": {
                "type": "float",
                "range": "[0.0, 1.0]",
                "meaning": "Fraction of cookies with SameSite=Strict",
                "source": "Set-Cookie header parsing",
                "missing_possible": False,
                "used_by_model": True,
                "limitation": "Same limitation; cookies without SameSite attribute count as 0 in all three ratios",
            },
            "cookie_samesite_lax_ratio": {
                "type": "float",
                "range": "[0.0, 1.0]",
                "meaning": "Fraction of cookies with SameSite=Lax",
                "source": "Set-Cookie header parsing",
                "missing_possible": False,
                "used_by_model": True,
                "limitation": "Same limitation",
            },
            "cookie_samesite_none_ratio": {
                "type": "float",
                "range": "[0.0, 1.0]",
                "meaning": "Fraction of cookies with SameSite=None",
                "source": "Set-Cookie header parsing",
                "missing_possible": False,
                "used_by_model": True,
                "limitation": "Same limitation",
            },
            "server_header_present": {
                "type": "binary",
                "range": "{0, 1}",
                "meaning": "1 if Server header present, 0 otherwise. Raw value excluded.",
                "source": "Response headers",
                "missing_possible": False,
                "used_by_model": True,
            },
            "x_powered_by_present": {
                "type": "binary",
                "range": "{0, 1}",
                "meaning": "1 if X-Powered-By header present, 0 otherwise. Raw value excluded.",
                "source": "Response headers",
                "missing_possible": False,
                "used_by_model": True,
            },
        }


@dataclass
class DatasetMetadata:
    """
    Provenance and debugging metadata — NEVER used as model features.

    Separated explicitly to prevent accidental leakage into training.
    """
    # Source identification
    source_type: str = ""           # "live_scan" | "common_crawl_wat" | "synthetic"
    source_identifier: str = ""     # crawl ID, scan ID, etc.

    # Origin information (for grouping/dedup only)
    url: str = ""
    scheme: str = ""
    host: str = ""
    port: Optional[int] = None
    origin: str = ""                # scheme://host:port
    registrable_domain: str = ""    # eTLD+1 for leakage-safe splitting

    # Crawl/scan provenance
    crawl_timestamp: str = ""       # ISO8601
    warc_filename: str = ""         # if Common Crawl
    record_id: str = ""             # WARC record ID or scan ID

    # Raw header values (excluded from model)
    server_header_value: Optional[str] = None
    x_powered_by_value: Optional[str] = None
    content_type: Optional[str] = None

    # Additional context
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def extract_ml_features_from_production(features: "FeatureVector") -> MLFeaturesV1:
    """
    Adapter: Convert production FeatureVector (app.features.extractor.FeatureVector)
    to MLFeaturesV1.

    This keeps the ML feature contract decoupled from the production schema.
    """
    # Determine is_html from content_type
    is_html = 0
    if features.content_type:
        ct = features.content_type.lower()
        if ct.startswith("text/html"):
            is_html = 1

    # Cookie ratios: note the limitation — when cookie_count=0, all ratios are 0.0
    # which is indistinguishable from "cookies exist but none have the flag"
    # This is preserved from the production extractor behavior.

    return MLFeaturesV1(
        feature_schema_version=ML_FEATURE_SCHEMA_VERSION,
        status_code=features.status_code,
        is_html=is_html,
        https_enabled=1 if features.https_enabled else 0,
        hsts_present=1 if features.hsts_present else 0,
        csp_present=1 if features.csp_present else 0,
        x_content_type_options_present=1 if features.x_content_type_options_present else 0,
        x_frame_options_present=1 if features.x_frame_options_present else 0,
        referrer_policy_present=1 if features.referrer_policy_present else 0,
        permissions_policy_present=1 if features.permissions_policy_present else 0,
        cookie_count=features.cookie_count,
        cookie_secure_ratio=features.cookie_secure_ratio,
        cookie_httponly_ratio=features.cookie_httponly_ratio,
        cookie_samesite_strict_ratio=features.cookie_samesite_strict_ratio,
        cookie_samesite_lax_ratio=features.cookie_samesite_lax_ratio,
        cookie_samesite_none_ratio=features.cookie_samesite_none_ratio,
        server_header_present=1 if features.server_header_present else 0,
        x_powered_by_present=1 if features.x_powered_by_present else 0,
    )


def extract_metadata_from_production(
    features: "FeatureVector",
    validated_url,
    scan_id: str = "",
) -> DatasetMetadata:
    """
    Extract metadata from production scan for provenance tracking.
    """
    from urllib.parse import urlparse

    parsed = urlparse(validated_url.canonical_url)
    scheme = parsed.scheme
    host = parsed.hostname or ""
    port = parsed.port

    # Use default ports if not explicitly specified
    if port is None:
        port = 443 if scheme == "https" else 80

    origin = f"{scheme}://{host}" + (f":{port}" if port else "")

    # Extract registrable domain (eTLD+1) - simplified, will use publicsuffix2 in preprocessing
    registrable_domain = host  # Placeholder; real extraction in ml/preprocessing/normalize.py

    return DatasetMetadata(
        source_type="live_scan",
        source_identifier=scan_id,
        url=validated_url.canonical_url,
        scheme=scheme,
        host=host,
        port=port,
        origin=origin,
        registrable_domain=registrable_domain,
        crawl_timestamp="",  # Will be filled by scan timestamp
        warc_filename="",
        record_id=scan_id,
        server_header_value=features.server_header_value,
        x_powered_by_value=features.x_powered_by_value,
        content_type=features.content_type,
    )


# Forward reference for type hints
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.features.extractor import FeatureVector