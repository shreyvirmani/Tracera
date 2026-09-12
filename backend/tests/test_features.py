from datetime import UTC, datetime, timedelta

from app.collector.collector import CollectorResponse
from app.features.cookie_parser import extract_cookie_features, parse_set_cookie_header
from app.features.extractor import extract_features
from app.features.html_parser import extract_html_features
from app.features.http_extractor import extract_http_features
from app.features.schema import FeatureSchemaVersion, FeatureVector
from app.features.security_headers import extract_security_headers
from app.features.technology import extract_technology_features
from app.features.tls_extractor import extract_tls_features


class TestHTTPExtractor:
    def test_basic_http_features(self):
        response = CollectorResponse(
            status_code=200,
            headers={"content-type": "text/html", "server": "nginx", "x-powered-by": "Express"},
            content=b"<html>test</html>",
            content_type="text/html",
            response_time_ms=150.5,
            redirect_count=0,
            final_url="https://example.com/",
        )

        features = extract_http_features(response)

        assert features.status_code == 200
        assert features.response_size_bytes == 17
        assert features.response_time_ms == 150.5
        assert features.content_type == "text/html"
        assert features.redirect_count == 0
        assert features.https_enabled is True
        assert features.server_header == "nginx"
        assert features.x_powered_by == "Express"

    def test_http_not_https(self):
        response = CollectorResponse(
            status_code=200,
            headers={},
            content=b"test",
            content_type="text/plain",
            response_time_ms=50.0,
            redirect_count=0,
            final_url="http://example.com/",
        )

        features = extract_http_features(response)
        assert features.https_enabled is False

    def test_redirect_count(self):
        response = CollectorResponse(
            status_code=200,
            headers={},
            content=b"test",
            content_type="text/plain",
            response_time_ms=50.0,
            redirect_count=3,
            final_url="https://example.com/",
        )

        features = extract_http_features(response)
        assert features.redirect_count == 3

    def test_missing_content_length(self):
        response = CollectorResponse(
            status_code=200,
            headers={},
            content=b"hello world",
            content_type="text/plain",
            response_time_ms=50.0,
            redirect_count=0,
            final_url="https://example.com/",
        )

        features = extract_http_features(response)
        assert features.response_size_bytes == 11


class TestSecurityHeadersExtractor:
    def test_all_security_headers_present(self):
        response = CollectorResponse(
            status_code=200,
            headers={
                "strict-transport-security": "max-age=31536000",
                "content-security-policy": "default-src 'self'",
                "x-content-type-options": "nosniff",
                "x-frame-options": "DENY",
                "referrer-policy": "strict-origin-when-cross-origin",
                "permissions-policy": "geolocation=()",
                "cross-origin-embedder-policy": "require-corp",
                "cross-origin-opener-policy": "same-origin",
                "cross-origin-resource-policy": "same-origin",
            },
            content=b"",
            content_type="text/html",
            response_time_ms=50.0,
            redirect_count=0,
            final_url="https://example.com/",
        )

        features = extract_security_headers(response)

        assert features.hsts == "max-age=31536000"
        assert features.csp == "default-src 'self'"
        assert features.x_content_type_options == "nosniff"
        assert features.x_frame_options == "DENY"
        assert features.referrer_policy == "strict-origin-when-cross-origin"
        assert features.permissions_policy == "geolocation=()"
        assert features.cross_origin_embedder_policy == "require-corp"
        assert features.cross_origin_opener_policy == "same-origin"
        assert features.cross_origin_resource_policy == "same-origin"

    def test_no_security_headers(self):
        response = CollectorResponse(
            status_code=200,
            headers={},
            content=b"",
            content_type="text/html",
            response_time_ms=50.0,
            redirect_count=0,
            final_url="https://example.com/",
        )

        features = extract_security_headers(response)

        assert features.hsts is None
        assert features.csp is None
        assert features.x_content_type_options is None
        assert features.x_frame_options is None
        assert features.referrer_policy is None
        assert features.permissions_policy is None


class TestCookieParser:
    def test_parse_simple_cookie(self):
        cookie = parse_set_cookie_header("session=abc123")
        assert cookie.name == "session"
        assert cookie.value == "abc123"
        assert cookie.secure is False
        assert cookie.httponly is False

    def test_parse_secure_httponly_cookie(self):
        cookie = parse_set_cookie_header("session=abc123; Secure; HttpOnly")
        assert cookie.secure is True
        assert cookie.httponly is True

    def test_parse_samesite_cookie(self):
        cookie = parse_set_cookie_header("session=abc123; SameSite=Strict")
        assert cookie.samesite == "strict"

    def test_parse_cookie_with_domain_path(self):
        cookie = parse_set_cookie_header("session=abc123; Domain=.example.com; Path=/")
        assert cookie.domain == ".example.com"
        assert cookie.path == "/"

    def test_parse_cookie_with_expires(self):
        cookie = parse_set_cookie_header("session=abc123; Expires=Wed, 21 Oct 2025 07:28:00 GMT")
        assert cookie.expires == "wed, 21 oct 2025 07:28:00 gmt"

    def test_parse_cookie_with_max_age(self):
        cookie = parse_set_cookie_header("session=abc123; Max-Age=3600")
        assert cookie.max_age == 3600


class TestCookieFeatureExtractor:
    def test_extract_cookie_features(self):
        response = CollectorResponse(
            status_code=200,
            headers={
                "set-cookie": [
                    "session=abc123; Secure; HttpOnly; SameSite=Strict",
                    "tracking=xyz789; Domain=.example.com",
                ],
            },
            content=b"",
            content_type="text/html",
            response_time_ms=50.0,
            redirect_count=0,
            final_url="https://example.com/",
        )

        features = extract_cookie_features(response)

        assert features.total_cookies == 2
        assert features.secure_cookies == 1
        assert features.httponly_cookies == 1
        assert features.samesite_cookies == 1
        assert features.session_cookies == 2
        assert features.persistent_cookies == 0
        assert features.third_party_indicators == 1

    def test_no_cookies(self):
        response = CollectorResponse(
            status_code=200,
            headers={},
            content=b"",
            content_type="text/html",
            response_time_ms=50.0,
            redirect_count=0,
            final_url="https://example.com/",
        )

        features = extract_cookie_features(response)

        assert features.total_cookies == 0
        assert features.secure_cookies == 0
        assert features.httponly_cookies == 0
        assert features.samesite_cookies == 0


class TestTLSExtractor:
    def test_http_returns_empty(self):
        response = CollectorResponse(
            status_code=200,
            headers={},
            content=b"",
            content_type="text/html",
            response_time_ms=50.0,
            redirect_count=0,
            final_url="http://example.com/",
        )

        features = extract_tls_features(response)

        assert features.cert_expiry_days is None
        assert features.cert_expired is False
        assert features.tls_version is None

    def test_https_with_tls_info(self):
        from datetime import datetime, timedelta

        future_date = (datetime.now(UTC) + timedelta(days=365)).isoformat().replace("+00:00", "Z")
        response = CollectorResponse(
            status_code=200,
            headers={},
            content=b"",
            content_type="text/html",
            response_time_ms=50.0,
            redirect_count=0,
            final_url="https://example.com/",
            tls_info={
                "tls_version": "TLSv1.3",
                "cipher_suite": "TLS_AES_256_GCM_SHA384",
                "certificate": {
                    "not_after": future_date,
                    "subject": "CN=example.com",
                    "issuer": "CN=Let's Encrypt",
                    "subject_alt_names": ["example.com", "www.example.com"],
                },
            },
        )

        features = extract_tls_features(response)

        assert features.tls_version == "TLSv1.3"
        assert features.cipher_suite == "TLS_AES_256_GCM_SHA384"
        assert features.cert_subject == "CN=example.com"
        assert features.cert_issuer == "CN=Let's Encrypt"
        assert features.san_count == 2
        assert features.cert_expiry_days is not None
        assert features.cert_expired is False

    def test_expired_cert(self):
        past_date = (datetime.now(UTC) - timedelta(days=1)).isoformat()
        response = CollectorResponse(
            status_code=200,
            headers={},
            content=b"",
            content_type="text/html",
            response_time_ms=50.0,
            redirect_count=0,
            final_url="https://example.com/",
            tls_info={
                "certificate": {
                    "not_after": past_date,
                },
            },
        )

        features = extract_tls_features(response)
        assert features.cert_expired is True


class TestHTMLParser:
    def test_basic_html_features(self):
        html = b"""
        <html>
            <head><title>Test</title></head>
            <body>
                <script src="/app.js"></script>
                <script src="https://cdn.example.com/lib.js"></script>
                <link rel="stylesheet" href="/style.css">
                <img src="/image.png">
                <img src="https://cdn.example.com/img.jpg">
                <iframe src="/frame.html"></iframe>
                <form action="/submit"><input type="password" name="pwd"></form>
                <form action="https://other.com/upload"><input type="file" name="f"></form>
            </body>
        </html>
        """

        response = CollectorResponse(
            status_code=200,
            headers={"content-type": "text/html"},
            content=html,
            content_type="text/html",
            response_time_ms=50.0,
            redirect_count=0,
            final_url="https://example.com/",
        )

        features = extract_html_features(response, "https://example.com/")

        assert features.html_size_bytes == len(html)
        assert features.script_count == 2
        assert features.stylesheet_count == 1
        assert features.image_count == 2
        assert features.iframe_count == 1
        assert features.form_count == 2
        assert features.external_domain_count == 2
        assert features.mixed_content_count == 0
        assert features.has_password_field is True
        assert features.has_file_upload is True

    def test_mixed_content_detection(self):
        html = b"""
        <html>
            <body>
                <script src="http://insecure.com/script.js"></script>
                <img src="http://insecure.com/image.jpg">
            </body>
        </html>
        """

        response = CollectorResponse(
            status_code=200,
            headers={"content-type": "text/html"},
            content=html,
            content_type="text/html",
            response_time_ms=50.0,
            redirect_count=0,
            final_url="https://example.com/",
        )

        features = extract_html_features(response, "https://example.com/")

        assert features.mixed_content_count == 2

    def test_non_html_content(self):
        response = CollectorResponse(
            status_code=200,
            headers={"content-type": "application/json"},
            content=b'{"key": "value"}',
            content_type="application/json",
            response_time_ms=50.0,
            redirect_count=0,
            final_url="https://example.com/",
        )

        features = extract_html_features(response, "https://example.com/")

        assert features.script_count == 0
        assert features.stylesheet_count == 0
        assert features.image_count == 0


class TestTechnologyExtractor:
    def test_detects_express(self):
        response = CollectorResponse(
            status_code=200,
            headers={"x-powered-by": "Express"},
            content=b"",
            content_type="text/html",
            response_time_ms=50.0,
            redirect_count=0,
            final_url="https://example.com/",
        )

        features = extract_technology_features(response)

        assert features.x_powered_by_present is True
        assert "express" in features.framework_indicators

    def test_detects_server_header(self):
        response = CollectorResponse(
            status_code=200,
            headers={"server": "nginx/1.20.1"},
            content=b"",
            content_type="text/html",
            response_time_ms=50.0,
            redirect_count=0,
            final_url="https://example.com/",
        )

        features = extract_technology_features(response)

        assert features.server_header_present is True
        assert "nginx" in features.framework_indicators

    def test_detects_multiple_frameworks(self):
        html = b'<script src="/_next/static/chunks/main.js"></script>'
        response = CollectorResponse(
            status_code=200,
            headers={"server": "nginx", "x-powered-by": "Next.js"},
            content=html,
            content_type="text/html",
            response_time_ms=50.0,
            redirect_count=0,
            final_url="https://example.com/",
        )

        features = extract_technology_features(response)

        assert "nginx" in features.framework_indicators
        assert "next.js" in features.framework_indicators


class TestFullFeatureExtraction:
    def test_extract_features_returns_feature_vector(self):
        html = b"""
        <html>
            <head><title>Test</title></head>
            <body>
                <script src="/app.js"></script>
                <form><input type="password"></form>
            </body>
        </html>
        """

        response = CollectorResponse(
            status_code=200,
            headers={
                "content-type": "text/html",
                "server": "nginx",
                "strict-transport-security": "max-age=31536000",
                "set-cookie": "session=abc; Secure; HttpOnly; SameSite=Lax",
            },
            content=html,
            content_type="text/html",
            response_time_ms=150.0,
            redirect_count=1,
            final_url="https://example.com/",
        )

        features = extract_features(response)

        assert isinstance(features, FeatureVector)
        assert features.feature_schema_version == FeatureSchemaVersion.V1
        assert features.http.status_code == 200
        assert features.http.https_enabled is True
        assert features.security_headers.hsts == "max-age=31536000"
        assert features.cookies.total_cookies == 1
        assert features.cookies.secure_cookies == 1
        assert features.html.script_count == 1
        assert features.html.form_count == 1
        assert features.html.has_password_field is True
        assert features.technology.server_header_present is True
        assert "nginx" in features.technology.framework_indicators

    def test_deterministic_extraction(self):
        html = b"<html><body><script src='/a.js'></script></body></html>"
        response = CollectorResponse(
            status_code=200,
            headers={"content-type": "text/html", "server": "nginx"},
            content=html,
            content_type="text/html",
            response_time_ms=100.0,
            redirect_count=0,
            final_url="https://example.com/",
        )

        features1 = extract_features(response)
        features2 = extract_features(response)

        assert features1.http.status_code == features2.http.status_code
        assert features1.html.script_count == features2.html.script_count
        assert (
            features1.technology.framework_indicators == features2.technology.framework_indicators
        )
