from dataclasses import dataclass
from typing import Optional
from enum import Enum

from app.features.extractor import FeatureVector


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Category(str, Enum):
    SECURITY = "security"
    CONFIGURATION = "configuration"
    PERFORMANCE = "performance"
    PRIVACY = "privacy"


@dataclass
class Finding:
    rule_id: str
    category: Category
    severity: Severity
    title: str
    description: str
    evidence: dict
    recommendation: str
    source: str = "rule_engine"
    confidence: float = 1.0


class Rule:
    def __init__(self, rule_id: str, category: Category, severity: Severity, title: str, description: str, recommendation: str):
        self.rule_id = rule_id
        self.category = category
        self.severity = severity
        self.title = title
        self.description = description
        self.recommendation = recommendation

    def check(self, features: FeatureVector) -> Optional[Finding]:
        raise NotImplementedError


class NoHTTPSRule(Rule):
    def __init__(self):
        super().__init__(
            rule_id="SEC-HTTPS-001",
            category=Category.SECURITY,
            severity=Severity.HIGH,
            title="HTTP used instead of HTTPS",
            description="The website is served over unencrypted HTTP instead of HTTPS.",
            recommendation="Configure HTTPS with a valid TLS certificate and redirect all HTTP traffic to HTTPS.",
        )

    def check(self, features: FeatureVector) -> Optional[Finding]:
        if not features.https_enabled:
            return Finding(
                rule_id=self.rule_id,
                category=self.category,
                severity=self.severity,
                title=self.title,
                description=self.description,
                evidence={"url_scheme": "http", "https_enabled": False},
                recommendation=self.recommendation,
            )
        return None


class MissingHSTSRule(Rule):
    def __init__(self):
        super().__init__(
            rule_id="SEC-HSTS-001",
            category=Category.SECURITY,
            severity=Severity.MEDIUM,
            title="HSTS header is missing",
            description="The response does not include the Strict-Transport-Security header.",
            recommendation="Configure HSTS header with appropriate max-age and includeSubDomains after confirming HTTPS works correctly.",
        )

    def check(self, features: FeatureVector) -> Optional[Finding]:
        if features.https_enabled and not features.hsts_present:
            return Finding(
                rule_id=self.rule_id,
                category=self.category,
                severity=self.severity,
                title=self.title,
                description=self.description,
                evidence={"header": "Strict-Transport-Security", "observed": False},
                recommendation=self.recommendation,
            )
        return None


class MissingCSPRule(Rule):
    def __init__(self):
        super().__init__(
            rule_id="SEC-CSP-001",
            category=Category.SECURITY,
            severity=Severity.MEDIUM,
            title="Content-Security-Policy header is missing",
            description="The response does not include a Content-Security-Policy header.",
            recommendation="Implement a restrictive CSP to mitigate XSS and injection attacks.",
        )

    def check(self, features: FeatureVector) -> Optional[Finding]:
        if not features.csp_present:
            return Finding(
                rule_id=self.rule_id,
                category=self.category,
                severity=self.severity,
                title=self.title,
                description=self.description,
                evidence={"header": "Content-Security-Policy", "observed": False},
                recommendation=self.recommendation,
            )
        return None


class MissingXContentTypeOptionsRule(Rule):
    def __init__(self):
        super().__init__(
            rule_id="SEC-XCTO-001",
            category=Category.SECURITY,
            severity=Severity.LOW,
            title="X-Content-Type-Options header is missing",
            description="The response does not include X-Content-Type-Options: nosniff.",
            recommendation="Add X-Content-Type-Options: nosniff to prevent MIME type sniffing.",
        )

    def check(self, features: FeatureVector) -> Optional[Finding]:
        if not features.x_content_type_options_present:
            return Finding(
                rule_id=self.rule_id,
                category=self.category,
                severity=self.severity,
                title=self.title,
                description=self.description,
                evidence={"header": "X-Content-Type-Options", "observed": False},
                recommendation=self.recommendation,
            )
        return None


class MissingXFrameOptionsRule(Rule):
    def __init__(self):
        super().__init__(
            rule_id="SEC-XFO-001",
            category=Category.SECURITY,
            severity=Severity.MEDIUM,
            title="X-Frame-Options header is missing",
            description="The response does not include X-Frame-Options header.",
            recommendation="Set X-Frame-Options to DENY or SAMEORIGIN to prevent clickjacking.",
        )

    def check(self, features: FeatureVector) -> Optional[Finding]:
        if not features.x_frame_options_present:
            return Finding(
                rule_id=self.rule_id,
                category=self.category,
                severity=self.severity,
                title=self.title,
                description=self.description,
                evidence={"header": "X-Frame-Options", "observed": False},
                recommendation=self.recommendation,
            )
        return None


class MissingReferrerPolicyRule(Rule):
    def __init__(self):
        super().__init__(
            rule_id="SEC-RP-001",
            category=Category.SECURITY,
            severity=Severity.LOW,
            title="Referrer-Policy header is missing",
            description="The response does not include a Referrer-Policy header.",
            recommendation="Set Referrer-Policy to strict-origin-when-cross-origin or stricter.",
        )

    def check(self, features: FeatureVector) -> Optional[Finding]:
        if not features.referrer_policy_present:
            return Finding(
                rule_id=self.rule_id,
                category=self.category,
                severity=self.severity,
                title=self.title,
                description=self.description,
                evidence={"header": "Referrer-Policy", "observed": False},
                recommendation=self.recommendation,
            )
        return None


class MissingPermissionsPolicyRule(Rule):
    def __init__(self):
        super().__init__(
            rule_id="SEC-PP-001",
            category=Category.SECURITY,
            severity=Severity.LOW,
            title="Permissions-Policy header is missing",
            description="The response does not include a Permissions-Policy header.",
            recommendation="Configure Permissions-Policy to restrict browser features and APIs.",
        )

    def check(self, features: FeatureVector) -> Optional[Finding]:
        if not features.permissions_policy_present:
            return Finding(
                rule_id=self.rule_id,
                category=self.category,
                severity=self.severity,
                title=self.title,
                description=self.description,
                evidence={"header": "Permissions-Policy", "observed": False},
                recommendation=self.recommendation,
            )
        return None


class InsecureCookieRule(Rule):
    def __init__(self):
        super().__init__(
            rule_id="SEC-COOKIE-001",
            category=Category.SECURITY,
            severity=Severity.HIGH,
            title="Insecure cookie configuration",
            description="Cookies are missing Secure flag on HTTPS site.",
            recommendation="Set Secure flag on all cookies when serving over HTTPS.",
        )

    def check(self, features: FeatureVector) -> Optional[Finding]:
        if features.https_enabled and features.cookie_count > 0 and features.cookie_secure_ratio < 1.0:
            return Finding(
                rule_id=self.rule_id,
                category=self.category,
                severity=self.severity,
                title=self.title,
                description=self.description,
                evidence={
                    "cookie_count": features.cookie_count,
                    "secure_ratio": features.cookie_secure_ratio,
                },
                recommendation=self.recommendation,
            )
        return None


class MissingHttpOnlyRule(Rule):
    def __init__(self):
        super().__init__(
            rule_id="SEC-COOKIE-002",
            category=Category.SECURITY,
            severity=Severity.MEDIUM,
            title="HttpOnly flag missing on cookies",
            description="Cookies are missing HttpOnly flag, exposing them to client-side scripts.",
            recommendation="Set HttpOnly flag on all cookies that don't require JavaScript access.",
        )

    def check(self, features: FeatureVector) -> Optional[Finding]:
        if features.cookie_count > 0 and features.cookie_httponly_ratio < 1.0:
            return Finding(
                rule_id=self.rule_id,
                category=self.category,
                severity=self.severity,
                title=self.title,
                description=self.description,
                evidence={
                    "cookie_count": features.cookie_count,
                    "httponly_ratio": features.cookie_httponly_ratio,
                },
                recommendation=self.recommendation,
            )
        return None


class WeakSameSiteRule(Rule):
    def __init__(self):
        super().__init__(
            rule_id="SEC-COOKIE-003",
            category=Category.SECURITY,
            severity=Severity.MEDIUM,
            title="Weak or missing SameSite cookie attribute",
            description="Cookies have SameSite=None without Secure, or missing SameSite attribute.",
            recommendation="Set SameSite=Strict or SameSite=Lax for cookies. Use SameSite=None only with Secure flag for cross-site cookies.",
        )

    def check(self, features: FeatureVector) -> Optional[Finding]:
        if features.cookie_count > 0:
            none_ratio = features.cookie_samesite_none_ratio
            strict_ratio = features.cookie_samesite_strict_ratio
            lax_ratio = features.cookie_samesite_lax_ratio

            if none_ratio > 0 and features.https_enabled:
                return Finding(
                    rule_id=self.rule_id,
                    category=self.category,
                    severity=self.severity,
                    title=self.title,
                    description=self.description,
                    evidence={
                        "cookie_count": features.cookie_count,
                        "samesite_none_ratio": none_ratio,
                    },
                    recommendation=self.recommendation,
                )
            if strict_ratio + lax_ratio + none_ratio < 1.0:
                return Finding(
                    rule_id=self.rule_id,
                    category=self.category,
                    severity=self.severity,
                    title=self.title,
                    description="Cookies are missing SameSite attribute entirely.",
                    evidence={
                        "cookie_count": features.cookie_count,
                        "samesite_defined_ratio": strict_ratio + lax_ratio + none_ratio,
                    },
                    recommendation=self.recommendation,
                )
        return None


class ServerVersionDisclosureRule(Rule):
    def __init__(self):
        super().__init__(
            rule_id="CFG-SERVER-001",
            category=Category.CONFIGURATION,
            severity=Severity.LOW,
            title="Server version disclosure",
            description="The Server header reveals detailed version information.",
            recommendation="Configure the web server to hide or minimize version information in the Server header.",
        )

    def check(self, features: FeatureVector) -> Optional[Finding]:
        if features.server_header_present and features.server_header_value:
            value = features.server_header_value.lower()
            if any(c.isdigit() for c in value) and "/" in value:
                return Finding(
                    rule_id=self.rule_id,
                    category=self.category,
                    severity=self.severity,
                    title=self.title,
                    description=self.description,
                    evidence={"server_header": features.server_header_value},
                    recommendation=self.recommendation,
                )
        return None


class XPoweredByDisclosureRule(Rule):
    def __init__(self):
        super().__init__(
            rule_id="CFG-XPB-001",
            category=Category.CONFIGURATION,
            severity=Severity.LOW,
            title="X-Powered-By header discloses technology",
            description="The X-Powered-By header reveals framework/language version information.",
            recommendation="Remove or obfuscate the X-Powered-By header.",
        )

    def check(self, features: FeatureVector) -> Optional[Finding]:
        if features.x_powered_by_present and features.x_powered_by_value:
            return Finding(
                rule_id=self.rule_id,
                category=self.category,
                severity=self.severity,
                title=self.title,
                description=self.description,
                evidence={"x_powered_by_header": features.x_powered_by_value},
                recommendation=self.recommendation,
            )
        return None


class WildcardCORSWithCredentialsRule(Rule):
    def __init__(self):
        super().__init__(
            rule_id="SEC-CORS-001",
            category=Category.SECURITY,
            severity=Severity.HIGH,
            title="Wildcard CORS with credentials",
            description="CORS policy allows wildcard origin with credentials (inferred from cookie presence).",
            recommendation="Do not use Access-Control-Allow-Origin: * with credentials. Specify exact origins.",
        )

    def check(self, features: FeatureVector) -> Optional[Finding]:
        if features.cookie_count > 0:
            cors = features.evidence.get("cors", {}) if hasattr(features, "evidence") else {}
            return None
        return None


class MixedContentRule(Rule):
    def __init__(self):
        super().__init__(
            rule_id="SEC-MIXED-001",
            category=Category.SECURITY,
            severity=Severity.HIGH,
            title="Mixed content detected",
            description="HTTPS page loads resources over HTTP.",
            recommendation="Update all resource URLs to use HTTPS.",
        )

    def check(self, features: FeatureVector) -> Optional[Finding]:
        if features.https_enabled and features.mixed_content_count > 0:
            return Finding(
                rule_id=self.rule_id,
                category=self.category,
                severity=self.severity,
                title=self.title,
                description=self.description,
                evidence={"mixed_content_count": features.mixed_content_count},
                recommendation=self.recommendation,
            )
        return None


class ExcessiveResponseSizeRule(Rule):
    def __init__(self):
        super().__init__(
            rule_id="PERF-SIZE-001",
            category=Category.PERFORMANCE,
            severity=Severity.LOW,
            title="Excessive response size",
            description="The HTML response size is unusually large.",
            recommendation="Optimize HTML payload size, enable compression, and review included resources.",
        )

    def check(self, features: FeatureVector) -> Optional[Finding]:
        if features.html_size_bytes > 500_000:
            return Finding(
                rule_id=self.rule_id,
                category=self.category,
                severity=self.severity,
                title=self.title,
                description=self.description,
                evidence={"html_size_bytes": features.html_size_bytes},
                recommendation=self.recommendation,
            )
        return None


class CertificateExpiryRule(Rule):
    def __init__(self):
        super().__init__(
            rule_id="SEC-TLS-001",
            category=Category.SECURITY,
            severity=Severity.HIGH,
            title="TLS certificate is expired or expiring soon",
            description="The TLS certificate has expired or expires within 30 days.",
            recommendation="Renew the TLS certificate immediately.",
        )

    def check(self, features: FeatureVector) -> Optional[Finding]:
        if features.cert_expiry_days is not None:
            if features.cert_is_expired:
                return Finding(
                    rule_id=self.rule_id,
                    category=self.category,
                    severity=Severity.CRITICAL,
                    title="TLS certificate has expired",
                    description="The TLS certificate is expired.",
                    evidence={"expiry_days": features.cert_expiry_days, "expired": True},
                    recommendation="Renew the TLS certificate immediately.",
                )
            elif features.cert_expiry_days <= 30:
                return Finding(
                    rule_id=self.rule_id,
                    category=self.category,
                    severity=self.severity,
                    title=self.title,
                    description=self.description,
                    evidence={"expiry_days": features.cert_expiry_days, "expired": False},
                    recommendation=self.recommendation,
                )
        return None


class MissingSecurityHeadersRule(Rule):
    def __init__(self):
        super().__init__(
            rule_id="SEC-HEADERS-001",
            category=Category.SECURITY,
            severity=Severity.MEDIUM,
            title="Multiple critical security headers missing",
            description="Several important security headers are missing simultaneously.",
            recommendation="Implement all missing security headers: HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy.",
        )

    def check(self, features: FeatureVector) -> Optional[Finding]:
        missing = []
        if features.https_enabled and not features.hsts_present:
            missing.append("HSTS")
        if not features.csp_present:
            missing.append("CSP")
        if not features.x_frame_options_present:
            missing.append("X-Frame-Options")
        if not features.x_content_type_options_present:
            missing.append("X-Content-Type-Options")

        if len(missing) >= 3:
            return Finding(
                rule_id=self.rule_id,
                category=self.category,
                severity=self.severity,
                title=self.title,
                description=self.description,
                evidence={"missing_headers": missing},
                recommendation=self.recommendation,
            )
        return None


RULES = [
    NoHTTPSRule(),
    MissingHSTSRule(),
    MissingCSPRule(),
    MissingXContentTypeOptionsRule(),
    MissingXFrameOptionsRule(),
    MissingReferrerPolicyRule(),
    MissingPermissionsPolicyRule(),
    InsecureCookieRule(),
    MissingHttpOnlyRule(),
    WeakSameSiteRule(),
    ServerVersionDisclosureRule(),
    XPoweredByDisclosureRule(),
    MixedContentRule(),
    ExcessiveResponseSizeRule(),
    CertificateExpiryRule(),
    MissingSecurityHeadersRule(),
]


def run_rules(features: FeatureVector) -> list[Finding]:
    findings = []
    for rule in RULES:
        finding = rule.check(features)
        if finding:
            findings.append(finding)
    return findings