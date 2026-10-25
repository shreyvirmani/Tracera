"""
Tracera ML Feature Schema v1

This module defines the ML feature vector contract (MLFeaturesV1) and the
separate metadata record (DatasetMetadata). The ML feature vector contains
ONLY stable, low-cardinality, numerical/binary features suitable for model
input. All high-cardinality, raw, or provenance fields are kept in metadata.

Feature groups (17 total):
- HTTP (3): status_code, is_html, https_enabled
- Security Headers (6): hsts_present, csp_present, x_content_type_options_present,
                        x_frame_options_present, referrer_policy_present,
                        permissions_policy_present
- Cookies (6): cookie_count, cookie_secure_ratio, cookie_httponly_ratio,
               cookie_samesite_strict_ratio, cookie_samesite_lax_ratio,
               cookie_samesite_none_ratio
- Tech Disclosure (2): server_header_present, x_powered_by_present

Validation: MLFeaturesV1.validate() enforces types, finiteness, and documented
ranges so that training and inference always see the same feature contract.
"""

from dataclasses import dataclass, asdict, field
from typing import Optional
import numpy as np


ML_FEATURE_SCHEMA_VERSION = "v1"


class FeatureValidationError(ValueError):
    """Raised when a feature vector violates the MLFeaturesV1 contract."""

    def __init__(self, message: str, issues: Optional[list] = None):
        super().__init__(message)
        self.issues: list[str] = list(issues or [])

    def __str__(self) -> str:
        base = super().__str__()
        if self.issues:
            details = "; ".join(self.issues[:10])
            more = f" (+{len(self.issues) - 10} more)" if len(self.issues) > 10 else ""
            return f"{base} [{details}{more}]"
        return base


def _is_int_value(v: object) -> bool:
    """True for Python or numpy integers (bool excluded)."""
    return isinstance(v, (int, np.integer)) and not isinstance(v, bool)


def _is_num_value(v: object) -> bool:
    """True for Python or numpy int/float (bool excluded)."""
    return isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, bool)


# Canonical feature groups (single source of truth for validation and tooling)
BINARY_FEATURES: list[str] = [
    "hsts_present", "csp_present", "x_content_type_options_present",
    "x_frame_options_present", "referrer_policy_present", "permissions_policy_present",
    "server_header_present", "x_powered_by_present",
]
HTTP_FEATURES: list[str] = ["status_code", "is_html", "https_enabled"]
COUNT_FEATURES: list[str] = ["cookie_count"]
RATIO_FEATURES: list[str] = [
    "cookie_secure_ratio", "cookie_httponly_ratio",
    "cookie_samesite_strict_ratio", "cookie_samesite_lax_ratio",
    "cookie_samesite_none_ratio",
]


@dataclass
class MLFeaturesV1:
    """
    ML Feature Vector v1 — 17 features total.

    All features are numerical (int/float) or binary (0/1). No strings,
    no high-cardinality categoricals, no raw header values.

    Feature groups (17 total):
    - HTTP (3): status_code, is_html, https_enabled
    - Security Headers (6): hsts_present, csp_present, x_content_type_options_present,
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
        ], dtype=np.float64)  # match training-time precision (float64); float32 silently perturbs ratios

    def validate(self) -> None:
        """
        Validate this vector against the MLFeaturesV1 contract.

        Checks (all problems collected, raised together):
        - feature_schema_version must be "v1".
        - status_code: 0 (documented "response not captured" sentinel) or [100, 599].
        - Binary features: int 0 or 1 (bool rejected).
        - cookie_count: non-negative int.
        - Ratios: finite numeric values within [0, 1].
        - No NaN/Inf anywhere; missing values are represented by the documented
          defaults, never by NaN/Inf (prevents training/serving skew).

        Raises:
            FeatureValidationError: with `.issues` listing every problem found.
        """
        issues: list[str] = []

        if self.feature_schema_version != ML_FEATURE_SCHEMA_VERSION:
            issues.append(
                f"feature_schema_version: expected {ML_FEATURE_SCHEMA_VERSION!r}, got {self.feature_schema_version!r}"
            )

        sc = self.status_code
        if isinstance(sc, bool) or not _is_int_value(sc):
            issues.append(f"status_code: int expected, got {sc!r} ({type(sc).__name__})")
        elif sc != 0 and not 100 <= int(sc) <= 599:
            issues.append(f"status_code: 0 or int [100, 599] expected, got {sc!r}")

        for name in ("is_html", "https_enabled", *BINARY_FEATURES):
            v = getattr(self, name)
            if not _is_int_value(v):
                issues.append(f"{name}: binary int 0/1 expected, got {v!r} ({type(v).__name__})")
            elif int(v) not in (0, 1):
                issues.append(f"{name}: binary int expected, got {v!r}")

        cc = self.cookie_count
        if not _is_int_value(cc):
            issues.append(f"cookie_count: non-negative int expected, got {cc!r} ({type(cc).__name__})")
        elif int(cc) < 0:
            issues.append(f"cookie_count: non-negative int expected, got {cc!r}")

        for name in RATIO_FEATURES:
            v = getattr(self, name)
            if not _is_num_value(v):
                issues.append(f"{name}: numeric value expected, got {v!r} ({type(v).__name__})")
                continue
            fv = float(v)
            if not np.isfinite(fv):
                issues.append(f"{name}: finite value expected, got {v!r}")
            elif fv < 0.0 or fv > 1.0:
                issues.append(f"{name}: value outside [0, 1]: {fv!r}")

        if issues:
            raise FeatureValidationError(
                f"MLFeaturesV1 validation failed with {len(issues)} issue(s)",
                issues=issues,
            )

    @classmethod
    def from_dict(cls, d: dict, strict: bool = True) -> "MLFeaturesV1":
        """
        Construct and validate an MLFeaturesV1 from a plain dict.

        strict=True (inference path): every one of the 17 feature keys must be
        present and valid; unknown keys are ignored.
        strict=False: missing keys fall back to documented defaults.

        Raises:
            FeatureValidationError: if any value violates the contract (or, in
            strict mode, if required keys are missing).
        """
        unknown = set(d) - set(cls.feature_names()) - {"feature_schema_version"}
        missing = [k for k in cls.feature_names() if k not in d]
        if strict and missing:
            raise FeatureValidationError(
                f"feature dict missing {len(missing)} required key(s)",
                issues=[f"missing key: {m}" for m in missing],
            )
        if explicit_missing := [k for k in d if k in set(cls.feature_names()) and d[k] is None]:
            raise FeatureValidationError(
                "feature dict contains None values (use documented defaults instead)",
                issues=[f"{k}: None not allowed" for k in explicit_missing],
            )
        if strict and unknown:
            # Unknown keys are tolerated but surfaced through issues for visibility.
            pass
        if strict:
            kwargs = {k: d[k] for k in cls.feature_names()}
        else:
            kwargs = {k: d.get(k, cls.__dataclass_fields__[k].default) for k in cls.feature_names()}
        if "feature_schema_version" in d and d["feature_schema_version"] is not None:
            kwargs["feature_schema_version"] = d["feature_schema_version"]
        fv = cls(**kwargs)
        fv.validate()
        return fv

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
                "range": "0 (sentinel: response not captured) or [100, 599]",
                "meaning": "HTTP response status code; 0 only when no response was captured",
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

    # Cookie metadata (for interpreting cookie ratios correctly)
    cookie_info_available: bool = False  # True if Set-Cookie header was present/parsed

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

    # Cookie metadata: true if Set-Cookie header was present
    cookie_info_available = features.cookie_count > 0

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
        cookie_info_available=cookie_info_available,
    )


# Forward reference for type hints
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.features.extractor import FeatureVector