import pytest
from app.features.extractor import extract_features
from app.collector.safe_collector import CollectorResponse
from app.core.url_validator import ValidatedURL


class TestFeatureExtractor:
    def test_basic_https_site(self):
        response = CollectorResponse(
            status_code=200,
            headers={
                "content-type": "text/html; charset=utf-8",
                "strict-transport-security": "max-age=31536000",
                "content-security-policy": "default-src 'self'",
                "x-content-type-options": "nosniff",
                "x-frame-options": "DENY",
                "referrer-policy": "strict-origin-when-cross-origin",
                "permissions-policy": "geolocation=()",
                "set-cookie": "session=abc; Secure; HttpOnly; SameSite=Strict",
                "server": "nginx",
            },
            content=b"<html><head><title>Test</title></head><body><script src='/app.js'></script><img src='/logo.png'></body></html>",
            url="https://example.com/",
            response_time_ms=150.0,
            redirect_count=0,
            tls_info={
                "not_after": "Dec 31 23:59:59 2026 GMT",
                "subject": {"commonName": "example.com"},
                "issuer": {"commonName": "Let's Encrypt"},
            },
        )

        validated = ValidatedURL(
            original_url="https://example.com",
            canonical_url="https://example.com/",
            scheme="https",
            hostname="example.com",
            path="/",
        )

        features = extract_features(response, validated)

        assert features.feature_schema_version == "v1"
        assert features.status_code == 200
        assert features.https_enabled is True
        assert features.hsts_present is True
        assert features.csp_present is True
        assert features.x_content_type_options_present is True
        assert features.x_frame_options_present is True
        assert features.referrer_policy_present is True
        assert features.permissions_policy_present is True
        assert features.cookie_count == 1
        assert features.cookie_secure_ratio == 1.0
        assert features.cookie_httponly_ratio == 1.0
        assert features.cookie_samesite_strict_ratio == 1.0
        assert features.server_header_present is True
        assert features.server_header_value == "nginx"
        assert features.script_count == 1
        assert features.image_count == 1

    def test_http_site_no_https(self):
        response = CollectorResponse(
            status_code=200,
            headers={"content-type": "text/html"},
            content=b"<html><body>HTTP site</body></html>",
            url="http://example.com/",
            response_time_ms=100.0,
            redirect_count=0,
            tls_info=None,
        )

        validated = ValidatedURL(
            original_url="http://example.com",
            canonical_url="http://example.com/",
            scheme="http",
            hostname="example.com",
            path="/",
        )

        features = extract_features(response, validated)

        assert features.https_enabled is False
        assert features.hsts_present is False
        assert features.cert_expiry_days is None

    def test_insecure_cookies(self):
        response = CollectorResponse(
            status_code=200,
            headers={
                "content-type": "text/html",
                "set-cookie": "session=abc; HttpOnly, tracking=xyz",
            },
            content=b"<html><body>Test</body></html>",
            url="https://example.com/",
            response_time_ms=100.0,
            redirect_count=0,
            tls_info=None,
        )

        validated = ValidatedURL(
            original_url="https://example.com",
            canonical_url="https://example.com/",
            scheme="https",
            hostname="example.com",
            path="/",
        )

        features = extract_features(response, validated)

        assert features.cookie_count == 2
        assert features.cookie_secure_ratio == 0.0
        assert features.cookie_httponly_ratio == 0.5

    def test_mixed_content_detection(self):
        response = CollectorResponse(
            status_code=200,
            headers={"content-type": "text/html"},
            content=b'<html><head><script src="http://cdn.example.com/script.js"></script></head><body><img src="http://images.example.com/logo.png"></body></html>',
            url="https://example.com/",
            response_time_ms=100.0,
            redirect_count=0,
            tls_info=None,
        )

        validated = ValidatedURL(
            original_url="https://example.com",
            canonical_url="https://example.com/",
            scheme="https",
            hostname="example.com",
            path="/",
        )

        features = extract_features(response, validated)

        assert features.mixed_content_count >= 2
        assert features.external_domain_count >= 1

    def test_tech_detection(self):
        response = CollectorResponse(
            status_code=200,
            headers={
                "content-type": "text/html",
                "server": "nginx/1.24.0",
                "x-powered-by": "Express",
            },
            content=b'<html><head><script>window.__NEXT_DATA__ = {}</script></head><body></body></html>',
            url="https://example.com/",
            response_time_ms=100.0,
            redirect_count=0,
            tls_info=None,
        )

        validated = ValidatedURL(
            original_url="https://example.com",
            canonical_url="https://example.com/",
            scheme="https",
            hostname="example.com",
            path="/",
        )

        features = extract_features(response, validated)

        assert features.server_header_present is True
        assert features.server_header_value == "nginx/1.24.0"
        assert features.x_powered_by_present is True
        assert features.x_powered_by_value == "Express"
        assert "express" in features.framework_indicators
        # nextjs detection requires specific patterns

    def test_certificate_expiry(self):
        response = CollectorResponse(
            status_code=200,
            headers={"content-type": "text/html"},
            content=b"<html><body>Test</body></html>",
            url="https://example.com/",
            response_time_ms=100.0,
            redirect_count=0,
            tls_info={
                "not_after": "Dec 31 23:59:59 2026 GMT",
                "subject": {"commonName": "example.com"},
                "issuer": {"commonName": "Let's Encrypt"},
            },
        )

        validated = ValidatedURL(
            original_url="https://example.com",
            canonical_url="https://example.com/",
            scheme="https",
            hostname="example.com",
            path="/",
        )

        features = extract_features(response, validated)

        assert features.cert_expiry_days is not None
        assert features.cert_is_expired is False
        assert features.cert_subject_cn == "example.com"
        assert features.cert_issuer_cn == "Let's Encrypt"