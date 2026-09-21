from app.features.schema import (
    CookieFeatures,
    FeatureVector,
    HTMLFeatures,
    HTTPFeatures,
    SecurityHeaderFeatures,
    TechnologyFeatures,
    TLSFeatures,
)
from app.rules import registry
from app.rules.configuration import (
    ServerVersionDisclosureRule,
    WildcardCORSWithCredentialsRule,
    XPoweredByDisclosureRule,
)
from app.rules.cookies import (
    InsecureCookieRule,
    MissingHttpOnlyRule,
    WeakSameSiteRule,
)
from app.rules.models import RuleResult
from app.rules.performance import (
    ExcessiveResponseSizeRule,
    MixedContentRule,
)
from app.rules.security import (
    HTTPSOnlyRule,
    MissingCSPRule,
    MissingHSTSRule,
    MissingPermissionsPolicyRule,
    MissingReferrerPolicyRule,
    MissingXContentTypeOptionsRule,
    MissingXFrameOptionsRule,
)


def make_feature_vector(**overrides) -> FeatureVector:
    defaults = {
        "http": HTTPFeatures(
            status_code=200,
            response_size_bytes=1000,
            response_time_ms=100.0,
            content_type="text/html",
            redirect_count=0,
            https_enabled=True,
            server_header=None,
            x_powered_by=None,
        ),
        "security_headers": SecurityHeaderFeatures(),
        "cookies": CookieFeatures(
            total_cookies=0,
            secure_cookies=0,
            httponly_cookies=0,
            samesite_cookies=0,
            session_cookies=0,
            persistent_cookies=0,
            third_party_indicators=0,
        ),
        "tls": TLSFeatures(),
        "html": HTMLFeatures(
            html_size_bytes=1000,
            script_count=0,
            stylesheet_count=0,
            image_count=0,
            iframe_count=0,
            form_count=0,
            external_domain_count=0,
            mixed_content_count=0,
        ),
        "technology": TechnologyFeatures(),
    }
    defaults.update(overrides)
    return FeatureVector(**defaults)


class TestHTTPSOnlyRule:
    def test_triggers_on_http(self):
        rule = HTTPSOnlyRule()
        features = make_feature_vector(
            http=HTTPFeatures(
                status_code=200,
                response_size_bytes=1000,
                response_time_ms=100.0,
                content_type="text/html",
                redirect_count=0,
                https_enabled=False,
            ),
        )
        result = rule.check(features)
        assert result.triggered is True
        assert len(result.findings) == 1
        assert result.findings[0].rule_id == "SEC-HTTPS-001"
        assert result.findings[0].severity.value == "high"

    def test_passes_on_https(self):
        rule = HTTPSOnlyRule()
        features = make_feature_vector()
        result = rule.check(features)
        assert result.triggered is False


class TestMissingHSTSRule:
    def test_triggers_when_missing(self):
        rule = MissingHSTSRule()
        features = make_feature_vector()
        result = rule.check(features)
        assert result.triggered is True
        assert result.findings[0].rule_id == "SEC-HSTS-001"
        assert result.findings[0].severity.value == "medium"

    def test_passes_when_present(self):
        rule = MissingHSTSRule()
        features = make_feature_vector(
            security_headers=SecurityHeaderFeatures(hsts="max-age=31536000"),
        )
        result = rule.check(features)
        assert result.triggered is False


class TestMissingCSPRule:
    def test_triggers_when_missing(self):
        rule = MissingCSPRule()
        features = make_feature_vector()
        result = rule.check(features)
        assert result.triggered is True
        assert result.findings[0].rule_id == "SEC-CSP-001"
        assert result.findings[0].severity.value == "medium"

    def test_passes_when_present(self):
        rule = MissingCSPRule()
        features = make_feature_vector(
            security_headers=SecurityHeaderFeatures(csp="default-src 'self'"),
        )
        result = rule.check(features)
        assert result.triggered is False


class TestMissingXContentTypeOptionsRule:
    def test_triggers_when_missing(self):
        rule = MissingXContentTypeOptionsRule()
        features = make_feature_vector()
        result = rule.check(features)
        assert result.triggered is True
        assert result.findings[0].severity.value == "low"

    def test_passes_when_present(self):
        rule = MissingXContentTypeOptionsRule()
        features = make_feature_vector(
            security_headers=SecurityHeaderFeatures(x_content_type_options="nosniff"),
        )
        result = rule.check(features)
        assert result.triggered is False


class TestMissingXFrameOptionsRule:
    def test_triggers_when_missing(self):
        rule = MissingXFrameOptionsRule()
        features = make_feature_vector()
        result = rule.check(features)
        assert result.triggered is True
        assert result.findings[0].severity.value == "medium"

    def test_passes_when_present(self):
        rule = MissingXFrameOptionsRule()
        features = make_feature_vector(
            security_headers=SecurityHeaderFeatures(x_frame_options="DENY"),
        )
        result = rule.check(features)
        assert result.triggered is False


class TestMissingReferrerPolicyRule:
    def test_triggers_when_missing(self):
        rule = MissingReferrerPolicyRule()
        features = make_feature_vector()
        result = rule.check(features)
        assert result.triggered is True
        assert result.findings[0].severity.value == "low"

    def test_passes_when_present(self):
        rule = MissingReferrerPolicyRule()
        features = make_feature_vector(
            security_headers=SecurityHeaderFeatures(
                referrer_policy="strict-origin-when-cross-origin"
            ),
        )
        result = rule.check(features)
        assert result.triggered is False


class TestMissingPermissionsPolicyRule:
    def test_triggers_when_missing(self):
        rule = MissingPermissionsPolicyRule()
        features = make_feature_vector()
        result = rule.check(features)
        assert result.triggered is True
        assert result.findings[0].severity.value == "low"

    def test_passes_when_present(self):
        rule = MissingPermissionsPolicyRule()
        features = make_feature_vector(
            security_headers=SecurityHeaderFeatures(permissions_policy="geolocation=()"),
        )
        result = rule.check(features)
        assert result.triggered is False


class TestInsecureCookieRule:
    def test_triggers_when_cookies_missing_secure(self):
        rule = InsecureCookieRule()
        features = make_feature_vector(
            cookies=CookieFeatures(
                total_cookies=2,
                secure_cookies=1,
                httponly_cookies=2,
                samesite_cookies=2,
                session_cookies=2,
                persistent_cookies=0,
                third_party_indicators=0,
            ),
        )
        result = rule.check(features)
        assert result.triggered is True
        assert result.findings[0].rule_id == "SEC-COOKIE-001"
        assert result.findings[0].severity.value == "high"

    def test_passes_when_all_secure(self):
        rule = InsecureCookieRule()
        features = make_feature_vector(
            cookies=CookieFeatures(
                total_cookies=2,
                secure_cookies=2,
                httponly_cookies=2,
                samesite_cookies=2,
                session_cookies=2,
                persistent_cookies=0,
                third_party_indicators=0,
            ),
        )
        result = rule.check(features)
        assert result.triggered is False

    def test_passes_when_no_cookies(self):
        rule = InsecureCookieRule()
        features = make_feature_vector()
        result = rule.check(features)
        assert result.triggered is False


class TestMissingHttpOnlyRule:
    def test_triggers_when_cookies_missing_httponly(self):
        rule = MissingHttpOnlyRule()
        features = make_feature_vector(
            cookies=CookieFeatures(
                total_cookies=2,
                secure_cookies=2,
                httponly_cookies=1,
                samesite_cookies=2,
                session_cookies=2,
                persistent_cookies=0,
                third_party_indicators=0,
            ),
        )
        result = rule.check(features)
        assert result.triggered is True
        assert result.findings[0].rule_id == "SEC-COOKIE-002"
        assert result.findings[0].severity.value == "medium"

    def test_passes_when_all_httponly(self):
        rule = MissingHttpOnlyRule()
        features = make_feature_vector(
            cookies=CookieFeatures(
                total_cookies=2,
                secure_cookies=2,
                httponly_cookies=2,
                samesite_cookies=2,
                session_cookies=2,
                persistent_cookies=0,
                third_party_indicators=0,
            ),
        )
        result = rule.check(features)
        assert result.triggered is False


class TestWeakSameSiteRule:
    def test_triggers_when_cookies_missing_samesite(self):
        rule = WeakSameSiteRule()
        features = make_feature_vector(
            cookies=CookieFeatures(
                total_cookies=2,
                secure_cookies=2,
                httponly_cookies=2,
                samesite_cookies=1,
                session_cookies=2,
                persistent_cookies=0,
                third_party_indicators=0,
            ),
        )
        result = rule.check(features)
        assert result.triggered is True
        assert result.findings[0].rule_id == "SEC-COOKIE-003"
        assert result.findings[0].severity.value == "medium"

    def test_passes_when_all_samesite(self):
        rule = WeakSameSiteRule()
        features = make_feature_vector(
            cookies=CookieFeatures(
                total_cookies=2,
                secure_cookies=2,
                httponly_cookies=2,
                samesite_cookies=2,
                session_cookies=2,
                persistent_cookies=0,
                third_party_indicators=0,
            ),
        )
        result = rule.check(features)
        assert result.triggered is False


class TestServerVersionDisclosureRule:
    def test_triggers_when_version_in_server_header(self):
        rule = ServerVersionDisclosureRule()
        features = make_feature_vector(
            http=HTTPFeatures(
                status_code=200,
                response_size_bytes=1000,
                response_time_ms=100.0,
                content_type="text/html",
                redirect_count=0,
                https_enabled=True,
                server_header="nginx/1.20.1",
                x_powered_by=None,
            ),
        )
        result = rule.check(features)
        assert result.triggered is True
        assert result.findings[0].rule_id == "CFG-SERVER-001"
        assert result.findings[0].severity.value == "low"

    def test_passes_when_generic_server(self):
        rule = ServerVersionDisclosureRule()
        features = make_feature_vector(
            http=HTTPFeatures(
                status_code=200,
                response_size_bytes=1000,
                response_time_ms=100.0,
                content_type="text/html",
                redirect_count=0,
                https_enabled=True,
                server_header="nginx",
                x_powered_by=None,
            ),
        )
        result = rule.check(features)
        assert result.triggered is False

    def test_passes_when_no_server_header(self):
        rule = ServerVersionDisclosureRule()
        features = make_feature_vector()
        result = rule.check(features)
        assert result.triggered is False


class TestXPoweredByDisclosureRule:
    def test_triggers_when_present(self):
        rule = XPoweredByDisclosureRule()
        features = make_feature_vector(
            http=HTTPFeatures(
                status_code=200,
                response_size_bytes=1000,
                response_time_ms=100.0,
                content_type="text/html",
                redirect_count=0,
                https_enabled=True,
                server_header=None,
                x_powered_by="Express",
            ),
        )
        result = rule.check(features)
        assert result.triggered is True
        assert result.findings[0].rule_id == "CFG-XPB-001"
        assert result.findings[0].severity.value == "low"

    def test_passes_when_absent(self):
        rule = XPoweredByDisclosureRule()
        features = make_feature_vector()
        result = rule.check(features)
        assert result.triggered is False


class TestWildcardCORSWithCredentialsRule:
    def test_triggers_when_wildcard_with_credentials(self):
        rule = WildcardCORSWithCredentialsRule()
        features = make_feature_vector(
            security_headers=SecurityHeaderFeatures(
                access_control_allow_origin="*",
                access_control_allow_credentials="true",
            ),
        )
        result = rule.check(features)
        assert result.triggered is True
        assert result.findings[0].rule_id == "SEC-CORS-001"
        assert result.findings[0].severity.value == "high"

    def test_passes_when_no_wildcard(self):
        rule = WildcardCORSWithCredentialsRule()
        features = make_feature_vector(
            security_headers=SecurityHeaderFeatures(
                access_control_allow_origin="https://example.com",
                access_control_allow_credentials="true",
            ),
        )
        result = rule.check(features)
        assert result.triggered is False

    def test_passes_when_no_credentials(self):
        rule = WildcardCORSWithCredentialsRule()
        features = make_feature_vector(
            security_headers=SecurityHeaderFeatures(
                access_control_allow_origin="*",
                access_control_allow_credentials="false",
            ),
        )
        result = rule.check(features)
        assert result.triggered is False


class TestMixedContentRule:
    def test_triggers_when_mixed_content(self):
        rule = MixedContentRule()
        features = make_feature_vector(
            html=HTMLFeatures(
                html_size_bytes=1000,
                script_count=1,
                stylesheet_count=0,
                image_count=0,
                iframe_count=0,
                form_count=0,
                external_domain_count=0,
                mixed_content_count=2,
            ),
        )
        result = rule.check(features)
        assert result.triggered is True
        assert result.findings[0].rule_id == "SEC-MIXED-001"
        assert result.findings[0].severity.value == "high"

    def test_passes_when_no_mixed_content(self):
        rule = MixedContentRule()
        features = make_feature_vector()
        result = rule.check(features)
        assert result.triggered is False


class TestExcessiveResponseSizeRule:
    def test_triggers_when_over_threshold(self):
        rule = ExcessiveResponseSizeRule()
        features = make_feature_vector(
            http=HTTPFeatures(
                status_code=200,
                response_size_bytes=15_000_000,
                response_time_ms=100.0,
                content_type="text/html",
                redirect_count=0,
                https_enabled=True,
            ),
        )
        result = rule.check(features)
        assert result.triggered is True
        assert result.findings[0].rule_id == "PERF-SIZE-001"
        assert result.findings[0].severity.value == "low"

    def test_passes_when_under_threshold(self):
        rule = ExcessiveResponseSizeRule()
        features = make_feature_vector()
        result = rule.check(features)
        assert result.triggered is False


class TestRuleRegistry:
    def test_registry_has_15_rules(self):
        assert len(registry.get_all()) == 15

    def test_run_all_returns_results_for_all(self):
        features = make_feature_vector()
        results = registry.run_all(features)
        assert len(results) == 15
        for result in results:
            assert isinstance(result, RuleResult)
            assert result.rule_id
