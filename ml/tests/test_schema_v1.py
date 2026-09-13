"""
Tests for ML Feature Schema v1.

Validates:
- Feature vector construction
- Feature array conversion (fixed order)
- Feature names and spec
- Metadata separation
- Adapter from production FeatureVector
- Cookie semantics edge cases
"""

import pytest
import numpy as np
from ml.features.schema_v1 import (
    MLFeaturesV1,
    DatasetMetadata,
    ML_FEATURE_SCHEMA_VERSION,
    extract_ml_features_from_production,
    extract_metadata_from_production,
)


class TestMLFeaturesV1:
    """Test ML feature vector construction and properties."""

    def test_default_construction(self):
        """Test default values produce valid feature vector."""
        f = MLFeaturesV1()
        assert f.feature_schema_version == ML_FEATURE_SCHEMA_VERSION
        assert f.status_code == 0
        assert f.is_html == 0
        assert f.https_enabled == 0
        # All binary features default to 0
        assert f.hsts_present == 0
        assert f.csp_present == 0
        assert f.cookie_count == 0
        assert f.cookie_secure_ratio == 0.0

    def test_custom_construction(self):
        """Test construction with custom values."""
        f = MLFeaturesV1(
            status_code=200,
            is_html=1,
            https_enabled=1,
            hsts_present=1,
            csp_present=1,
            x_content_type_options_present=1,
            x_frame_options_present=1,
            referrer_policy_present=1,
            permissions_policy_present=1,
            cookie_count=3,
            cookie_secure_ratio=1.0,
            cookie_httponly_ratio=1.0,
            cookie_samesite_strict_ratio=0.5,
            cookie_samesite_lax_ratio=0.5,
            cookie_samesite_none_ratio=0.0,
            server_header_present=1,
            x_powered_by_present=0,
        )
        assert f.status_code == 200
        assert f.cookie_count == 3
        assert f.cookie_secure_ratio == 1.0

    def test_to_array_shape_and_dtype(self):
        """Test to_array returns correct shape and dtype."""
        f = MLFeaturesV1(
            status_code=200,
            is_html=1,
            https_enabled=1,
            hsts_present=1,
            csp_present=1,
            x_content_type_options_present=1,
            x_frame_options_present=1,
            referrer_policy_present=1,
            permissions_policy_present=1,
            cookie_count=2,
            cookie_secure_ratio=0.5,
            cookie_httponly_ratio=0.5,
            cookie_samesite_strict_ratio=0.5,
            cookie_samesite_lax_ratio=0.5,
            cookie_samesite_none_ratio=0.0,
            server_header_present=1,
            x_powered_by_present=0,
        )
        arr = f.to_array()
        assert arr.shape == (17,)  # 17 features total
        assert arr.dtype == np.float32

    def test_to_array_fixed_order(self):
        """Test feature order matches feature_names()."""
        f = MLFeaturesV1(
            status_code=200,
            is_html=1,
            https_enabled=1,
            hsts_present=1,
            csp_present=1,
            x_content_type_options_present=1,
            x_frame_options_present=1,
            referrer_policy_present=1,
            permissions_policy_present=1,
            cookie_count=2,
            cookie_secure_ratio=0.5,
            cookie_httponly_ratio=0.5,
            cookie_samesite_strict_ratio=0.5,
            cookie_samesite_lax_ratio=0.5,
            cookie_samesite_none_ratio=0.0,
            server_header_present=1,
            x_powered_by_present=0,
        )
        arr = f.to_array()
        names = MLFeaturesV1.feature_names()

        # Verify order by checking known positions
        assert names[0] == "status_code"
        assert arr[0] == 200.0
        assert names[1] == "is_html"
        assert arr[1] == 1.0
        assert names[2] == "https_enabled"
        assert arr[2] == 1.0
        # Security headers at positions 3-8
        assert names[3] == "hsts_present"
        assert names[8] == "permissions_policy_present"
        # Cookie count at 9
        assert names[9] == "cookie_count"
        assert arr[9] == 2.0
        # Cookie ratios at 10-14
        assert names[10] == "cookie_secure_ratio"
        assert names[14] == "cookie_samesite_none_ratio"
        # Tech disclosure at 15-16
        assert names[15] == "server_header_present"
        assert names[16] == "x_powered_by_present"

    def test_feature_names_length(self):
        """Test feature_names returns 17 names."""
        names = MLFeaturesV1.feature_names()
        assert len(names) == 17

    def test_feature_spec_complete(self):
        """Test feature_spec has entry for every feature."""
        spec = MLFeaturesV1.feature_spec()
        names = MLFeaturesV1.feature_names()
        assert set(spec.keys()) == set(names)
        for name in names:
            assert "type" in spec[name]
            assert "range" in spec[name]
            assert "meaning" in spec[name]
            assert "source" in spec[name]
            assert "missing_possible" in spec[name]
            assert "used_by_model" in spec[name]

    def test_to_dict_roundtrip(self):
        """Test to_dict produces correct dictionary."""
        f = MLFeaturesV1(status_code=200, is_html=1, https_enabled=1)
        d = f.to_dict()
        assert d["status_code"] == 200
        assert d["is_html"] == 1
        assert d["https_enabled"] == 1
        assert d["feature_schema_version"] == ML_FEATURE_SCHEMA_VERSION


class TestCookieSemantics:
    """
    Test cookie semantics — critical edge case.

    The production extractor returns 0.0 for all ratios when cookie_count=0
    (no Set-Cookie header). This is indistinguishable from "cookies exist
    but none have Secure/HttpOnly/SameSite". This test documents the
    limitation rather than fixing it (which would require production changes).
    """

    def test_zero_cookies_yields_zero_ratios(self):
        """When cookie_count=0, all ratios are 0.0."""
        f = MLFeaturesV1(cookie_count=0)
        assert f.cookie_secure_ratio == 0.0
        assert f.cookie_httponly_ratio == 0.0
        assert f.cookie_samesite_strict_ratio == 0.0
        assert f.cookie_samesite_lax_ratio == 0.0
        assert f.cookie_samesite_none_ratio == 0.0

    def test_cookies_exist_but_none_secure(self):
        """Cookies exist but none have Secure flag -> secure_ratio=0.0."""
        f = MLFeaturesV1(
            cookie_count=2,
            cookie_secure_ratio=0.0,
            cookie_httponly_ratio=0.5,
            cookie_samesite_strict_ratio=0.0,
            cookie_samesite_lax_ratio=1.0,
            cookie_samesite_none_ratio=0.0,
        )
        assert f.cookie_secure_ratio == 0.0
        assert f.cookie_httponly_ratio == 0.5
        assert f.cookie_samesite_lax_ratio == 1.0

    def test_ratio_bounds(self):
        """All ratios must be in [0.0, 1.0]."""
        f = MLFeaturesV1(
            cookie_count=1,
            cookie_secure_ratio=1.0,
            cookie_httponly_ratio=1.0,
            cookie_samesite_strict_ratio=1.0,
            cookie_samesite_lax_ratio=1.0,
            cookie_samesite_none_ratio=1.0,
        )
        assert 0.0 <= f.cookie_secure_ratio <= 1.0
        assert 0.0 <= f.cookie_httponly_ratio <= 1.0
        assert 0.0 <= f.cookie_samesite_strict_ratio <= 1.0
        assert 0.0 <= f.cookie_samesite_lax_ratio <= 1.0
        assert 0.0 <= f.cookie_samesite_none_ratio <= 1.0


class TestDatasetMetadata:
    """Test metadata separation."""

    def test_metadata_construction(self):
        """Test metadata can be constructed with all fields."""
        meta = DatasetMetadata(
            source_type="live_scan",
            source_identifier="scan-123",
            url="https://example.com/path",
            scheme="https",
            host="example.com",
            port=443,
            origin="https://example.com",
            registrable_domain="example.com",
            crawl_timestamp="2026-01-15T10:30:00Z",
            warc_filename="",
            record_id="scan-123",
            server_header_value="nginx/1.24",
            x_powered_by_value="Express",
            content_type="text/html; charset=utf-8",
        )
        assert meta.source_type == "live_scan"
        assert meta.registrable_domain == "example.com"
        assert meta.server_header_value == "nginx/1.24"

    def test_metadata_excludes_model_features(self):
        """Metadata should not contain any ML feature fields."""
        meta = DatasetMetadata()
        meta_dict = meta.to_dict()

        # These should NOT be in metadata
        model_features = MLFeaturesV1.feature_names()
        for mf in model_features:
            assert mf not in meta_dict, f"Model feature {mf} leaked into metadata"

    def test_metadata_extra_field(self):
        """Test extra dict for extensibility."""
        meta = DatasetMetadata(extra={"custom_field": "value"})
        assert meta.extra["custom_field"] == "value"


class TestProductionAdapter:
    """Test adapter from production FeatureVector to MLFeaturesV1."""

    def test_extract_ml_features_from_production(self):
        """Test adapter with a mock production FeatureVector."""
        # Create a mock production FeatureVector
        from dataclasses import dataclass
        from typing import Optional

        @dataclass
        class MockFeatureVector:
            feature_schema_version: str
            status_code: int
            response_size_bytes: int
            response_time_ms: float
            content_type: Optional[str]
            redirect_count: int
            https_enabled: bool
            hsts_present: bool
            csp_present: bool
            x_content_type_options_present: bool
            x_frame_options_present: bool
            referrer_policy_present: bool
            permissions_policy_present: bool
            cookie_count: int
            cookie_secure_ratio: float
            cookie_httponly_ratio: float
            cookie_samesite_strict_ratio: float
            cookie_samesite_lax_ratio: float
            cookie_samesite_none_ratio: float
            third_party_cookie_indicators: int
            cert_expiry_days: Optional[int]
            cert_is_expired: bool
            tls_version: Optional[str]
            cert_subject_cn: Optional[str]
            cert_issuer_cn: Optional[str]
            html_size_bytes: int
            script_count: int
            stylesheet_count: int
            image_count: int
            iframe_count: int
            form_count: int
            external_domain_count: int
            mixed_content_count: int
            server_header_present: bool
            server_header_value: Optional[str]
            x_powered_by_present: bool
            x_powered_by_value: Optional[str]
            framework_indicators: list[str]

        prod_features = MockFeatureVector(
            feature_schema_version="v1",
            status_code=200,
            response_size_bytes=1024,
            response_time_ms=150.0,
            content_type="text/html; charset=utf-8",
            redirect_count=0,
            https_enabled=True,
            hsts_present=True,
            csp_present=True,
            x_content_type_options_present=True,
            x_frame_options_present=True,
            referrer_policy_present=True,
            permissions_policy_present=True,
            cookie_count=2,
            cookie_secure_ratio=1.0,
            cookie_httponly_ratio=1.0,
            cookie_samesite_strict_ratio=0.5,
            cookie_samesite_lax_ratio=0.5,
            cookie_samesite_none_ratio=0.0,
            third_party_cookie_indicators=0,
            cert_expiry_days=30,
            cert_is_expired=False,
            tls_version="TLS 1.3",
            cert_subject_cn="example.com",
            cert_issuer_cn="Let's Encrypt",
            html_size_bytes=1024,
            script_count=5,
            stylesheet_count=2,
            image_count=10,
            iframe_count=0,
            form_count=1,
            external_domain_count=3,
            mixed_content_count=0,
            server_header_present=True,
            server_header_value="nginx/1.24",
            x_powered_by_present=False,
            x_powered_by_value=None,
            framework_indicators=["nginx"],
        )

        ml_features = extract_ml_features_from_production(prod_features)

        assert ml_features.status_code == 200
        assert ml_features.is_html == 1
        assert ml_features.https_enabled == 1
        assert ml_features.hsts_present == 1
        assert ml_features.csp_present == 1
        assert ml_features.cookie_count == 2
        assert ml_features.cookie_secure_ratio == 1.0
        assert ml_features.server_header_present == 1
        assert ml_features.x_powered_by_present == 0

    def test_extract_ml_features_non_html(self):
        """Test adapter with non-HTML content type."""
        from dataclasses import dataclass
        from typing import Optional

        @dataclass
        class MockFeatureVector:
            feature_schema_version: str
            status_code: int
            content_type: Optional[str]
            https_enabled: bool
            hsts_present: bool
            csp_present: bool
            x_content_type_options_present: bool
            x_frame_options_present: bool
            referrer_policy_present: bool
            permissions_policy_present: bool
            cookie_count: int
            cookie_secure_ratio: float
            cookie_httponly_ratio: float
            cookie_samesite_strict_ratio: float
            cookie_samesite_lax_ratio: float
            cookie_samesite_none_ratio: float
            server_header_present: bool
            x_powered_by_present: bool
            # Required but unused
            response_size_bytes: int = 0
            response_time_ms: float = 0.0
            redirect_count: int = 0
            third_party_cookie_indicators: int = 0
            cert_expiry_days: Optional[int] = None
            cert_is_expired: bool = False
            tls_version: Optional[str] = None
            cert_subject_cn: Optional[str] = None
            cert_issuer_cn: Optional[str] = None
            html_size_bytes: int = 0
            script_count: int = 0
            stylesheet_count: int = 0
            image_count: int = 0
            iframe_count: int = 0
            form_count: int = 0
            external_domain_count: int = 0
            mixed_content_count: int = 0
            server_header_value: Optional[str] = None
            x_powered_by_value: Optional[str] = None
            framework_indicators: list[str] = None

        prod_features = MockFeatureVector(
            feature_schema_version="v1",
            status_code=200,
            content_type="application/json",
            https_enabled=True,
            hsts_present=True,
            csp_present=False,
            x_content_type_options_present=False,
            x_frame_options_present=False,
            referrer_policy_present=False,
            permissions_policy_present=False,
            cookie_count=0,
            cookie_secure_ratio=0.0,
            cookie_httponly_ratio=0.0,
            cookie_samesite_strict_ratio=0.0,
            cookie_samesite_lax_ratio=0.0,
            cookie_samesite_none_ratio=0.0,
            server_header_present=False,
            x_powered_by_present=False,
        )

        ml_features = extract_ml_features_from_production(prod_features)

        assert ml_features.is_html == 0  # Not text/html
        assert ml_features.https_enabled == 1
        assert ml_features.hsts_present == 1
        assert ml_features.csp_present == 0


class TestMetadataAdapter:
    """Test metadata extraction from production."""

    def test_extract_metadata_from_production(self):
        """Test metadata adapter."""
        from dataclasses import dataclass
        from typing import Optional

        @dataclass
        class MockValidatedURL:
            canonical_url: str = "https://example.com/path"

        @dataclass
        class MockFeatureVector:
            feature_schema_version: str
            status_code: int
            content_type: Optional[str]
            https_enabled: bool
            hsts_present: bool
            csp_present: bool
            x_content_type_options_present: bool
            x_frame_options_present: bool
            referrer_policy_present: bool
            permissions_policy_present: bool
            cookie_count: int
            cookie_secure_ratio: float
            cookie_httponly_ratio: float
            cookie_samesite_strict_ratio: float
            cookie_samesite_lax_ratio: float
            cookie_samesite_none_ratio: float
            server_header_present: bool
            server_header_value: Optional[str]
            x_powered_by_present: bool
            x_powered_by_value: Optional[str]
            # Required but unused
            response_size_bytes: int = 0
            response_time_ms: float = 0.0
            redirect_count: int = 0
            third_party_cookie_indicators: int = 0
            cert_expiry_days: Optional[int] = None
            cert_is_expired: bool = False
            tls_version: Optional[str] = None
            cert_subject_cn: Optional[str] = None
            cert_issuer_cn: Optional[str] = None
            html_size_bytes: int = 0
            script_count: int = 0
            stylesheet_count: int = 0
            image_count: int = 0
            iframe_count: int = 0
            form_count: int = 0
            external_domain_count: int = 0
            mixed_content_count: int = 0
            framework_indicators: list[str] = None

        validated_url = MockValidatedURL()
        prod_features = MockFeatureVector(
            feature_schema_version="v1",
            status_code=200,
            content_type="text/html; charset=utf-8",
            https_enabled=True,
            hsts_present=True,
            csp_present=True,
            x_content_type_options_present=True,
            x_frame_options_present=True,
            referrer_policy_present=True,
            permissions_policy_present=True,
            cookie_count=2,
            cookie_secure_ratio=1.0,
            cookie_httponly_ratio=1.0,
            cookie_samesite_strict_ratio=0.5,
            cookie_samesite_lax_ratio=0.5,
            cookie_samesite_none_ratio=0.0,
            server_header_present=True,
            server_header_value="nginx/1.24",
            x_powered_by_present=False,
            x_powered_by_value=None,
        )

        metadata = extract_metadata_from_production(prod_features, validated_url, "scan-123")

        assert metadata.source_type == "live_scan"
        assert metadata.source_identifier == "scan-123"
        assert metadata.url == "https://example.com/path"
        assert metadata.scheme == "https"
        assert metadata.host == "example.com"
        assert metadata.port == 443
        assert metadata.origin == "https://example.com:443"  # Includes explicit default port
        assert metadata.registrable_domain == "example.com"
        assert metadata.server_header_value == "nginx/1.24"
        assert metadata.x_powered_by_value is None
        assert metadata.content_type == "text/html; charset=utf-8"


class TestSchemaVersion:
    """Test schema version enforcement."""

    def test_schema_version_constant(self):
        """Test ML_FEATURE_SCHEMA_VERSION is defined."""
        assert ML_FEATURE_SCHEMA_VERSION == "v1"

    def test_default_feature_vector_has_correct_version(self):
        """Test default FeatureVector has correct schema version."""
        f = MLFeaturesV1()
        assert f.feature_schema_version == "v1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])