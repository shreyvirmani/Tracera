import pytest
from app.rules.engine import run_rules, Finding, Severity, Category
from app.features.extractor import FeatureVector


def make_features(**overrides) -> FeatureVector:
    defaults = {
        "feature_schema_version": "v1",
        "status_code": 200,
        "response_size_bytes": 1000,
        "response_time_ms": 100.0,
        "content_type": "text/html",
        "redirect_count": 0,
        "https_enabled": True,
        "hsts_present": True,
        "csp_present": True,
        "x_content_type_options_present": True,
        "x_frame_options_present": True,
        "referrer_policy_present": True,
        "permissions_policy_present": True,
        "cookie_count": 1,
        "cookie_secure_ratio": 1.0,
        "cookie_httponly_ratio": 1.0,
        "cookie_samesite_strict_ratio": 1.0,
        "cookie_samesite_lax_ratio": 0.0,
        "cookie_samesite_none_ratio": 0.0,
        "third_party_cookie_indicators": 0,
        "cert_expiry_days": 365,
        "cert_is_expired": False,
        "tls_version": "TLS 1.3",
        "cert_subject_cn": "example.com",
        "cert_issuer_cn": "Let's Encrypt",
        "html_size_bytes": 1000,
        "script_count": 1,
        "stylesheet_count": 1,
        "image_count": 1,
        "iframe_count": 0,
        "form_count": 0,
        "external_domain_count": 0,
        "mixed_content_count": 0,
        "server_header_present": False,
        "server_header_value": None,
        "x_powered_by_present": False,
        "x_powered_by_value": None,
        "framework_indicators": [],
    }
    defaults.update(overrides)
    return FeatureVector(**defaults)


class TestRules:
    def test_no_https_triggers(self):
        features = make_features(https_enabled=False)
        findings = run_rules(features)
        rule_ids = [f.rule_id for f in findings]
        assert "SEC-HTTPS-001" in rule_ids

    def test_missing_hsts_triggers(self):
        features = make_features(https_enabled=True, hsts_present=False)
        findings = run_rules(features)
        rule_ids = [f.rule_id for f in findings]
        assert "SEC-HSTS-001" in rule_ids

    def test_missing_csp_triggers(self):
        features = make_features(csp_present=False)
        findings = run_rules(features)
        rule_ids = [f.rule_id for f in findings]
        assert "SEC-CSP-001" in rule_ids

    def test_missing_x_content_type_options_triggers(self):
        features = make_features(x_content_type_options_present=False)
        findings = run_rules(features)
        rule_ids = [f.rule_id for f in findings]
        assert "SEC-XCTO-001" in rule_ids

    def test_missing_x_frame_options_triggers(self):
        features = make_features(x_frame_options_present=False)
        findings = run_rules(features)
        rule_ids = [f.rule_id for f in findings]
        assert "SEC-XFO-001" in rule_ids

    def test_missing_referrer_policy_triggers(self):
        features = make_features(referrer_policy_present=False)
        findings = run_rules(features)
        rule_ids = [f.rule_id for f in findings]
        assert "SEC-RP-001" in rule_ids

    def test_missing_permissions_policy_triggers(self):
        features = make_features(permissions_policy_present=False)
        findings = run_rules(features)
        rule_ids = [f.rule_id for f in findings]
        assert "SEC-PP-001" in rule_ids

    def test_insecure_cookie_triggers(self):
        features = make_features(https_enabled=True, cookie_count=2, cookie_secure_ratio=0.5)
        findings = run_rules(features)
        rule_ids = [f.rule_id for f in findings]
        assert "SEC-COOKIE-001" in rule_ids

    def test_missing_httponly_triggers(self):
        features = make_features(cookie_count=2, cookie_httponly_ratio=0.5)
        findings = run_rules(features)
        rule_ids = [f.rule_id for f in findings]
        assert "SEC-COOKIE-002" in rule_ids

    def test_weak_samesite_none_triggers(self):
        features = make_features(https_enabled=True, cookie_count=1, cookie_samesite_none_ratio=1.0)
        findings = run_rules(features)
        rule_ids = [f.rule_id for f in findings]
        assert "SEC-COOKIE-003" in rule_ids

    def test_missing_samesite_triggers(self):
        features = make_features(cookie_count=1, cookie_samesite_strict_ratio=0.0, cookie_samesite_lax_ratio=0.0, cookie_samesite_none_ratio=0.0)
        findings = run_rules(features)
        rule_ids = [f.rule_id for f in findings]
        assert "SEC-COOKIE-003" in rule_ids

    def test_server_version_disclosure_triggers(self):
        features = make_features(server_header_present=True, server_header_value="nginx/1.24.0")
        findings = run_rules(features)
        rule_ids = [f.rule_id for f in findings]
        assert "CFG-SERVER-001" in rule_ids

    def test_x_powered_by_disclosure_triggers(self):
        features = make_features(x_powered_by_present=True, x_powered_by_value="Express")
        findings = run_rules(features)
        rule_ids = [f.rule_id for f in findings]
        assert "CFG-XPB-001" in rule_ids

    def test_mixed_content_triggers(self):
        features = make_features(https_enabled=True, mixed_content_count=2)
        findings = run_rules(features)
        rule_ids = [f.rule_id for f in findings]
        assert "SEC-MIXED-001" in rule_ids

    def test_excessive_response_size_triggers(self):
        features = make_features(html_size_bytes=600_000)
        findings = run_rules(features)
        rule_ids = [f.rule_id for f in findings]
        assert "PERF-SIZE-001" in rule_ids

    def test_cert_expired_triggers_critical(self):
        features = make_features(cert_expiry_days=-1, cert_is_expired=True)
        findings = run_rules(features)
        cert_findings = [f for f in findings if f.rule_id == "SEC-TLS-001"]
        assert len(cert_findings) == 1
        assert cert_findings[0].severity == Severity.CRITICAL

    def test_cert_expiring_soon_triggers_high(self):
        features = make_features(cert_expiry_days=15, cert_is_expired=False)
        findings = run_rules(features)
        cert_findings = [f for f in findings if f.rule_id == "SEC-TLS-001"]
        assert len(cert_findings) == 1
        assert cert_findings[0].severity == Severity.HIGH

    def test_multiple_security_headers_missing(self):
        features = make_features(
            https_enabled=True,
            hsts_present=False,
            csp_present=False,
            x_frame_options_present=False,
            x_content_type_options_present=False,
        )
        findings = run_rules(features)
        rule_ids = [f.rule_id for f in findings]
        assert "SEC-HEADERS-001" in rule_ids

    def test_all_secure_no_findings(self):
        features = make_features()
        findings = run_rules(features)
        security_findings = [f for f in findings if f.category == Category.SECURITY]
        assert len(security_findings) == 0