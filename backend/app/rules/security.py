from app.features.schema import FeatureVector
from app.rules.base import Rule
from app.rules.evidence import (
    HTTPNotHTTPSEvidence,
    MissingCSPEvidence,
    MissingHSTSEvidence,
    MissingPermissionsPolicyEvidence,
    MissingReferrerPolicyEvidence,
    MissingXContentTypeOptionsEvidence,
    MissingXFrameOptionsEvidence,
)
from app.rules.models import Category, RuleResult, Severity


class HTTPSOnlyRule(Rule):
    rule_id = "SEC-HTTPS-001"
    category = Category.SECURITY
    severity = Severity.HIGH
    title = "HTTP used instead of HTTPS"
    description = "The website is accessible via HTTP, which transmits data in plaintext and is vulnerable to interception and modification."
    recommendation = "Enforce HTTPS by redirecting all HTTP traffic to HTTPS and implementing HSTS."

    def check(self, features: FeatureVector) -> RuleResult:
        if not features.http.https_enabled:
            finding = self._create_finding(
                HTTPNotHTTPSEvidence(
                    final_url=features.http.content_type or "unknown",
                    scheme="http",
                )
            )
            return RuleResult(rule_id=self.rule_id, triggered=True, findings=[finding])
        return RuleResult(rule_id=self.rule_id, triggered=False)


class MissingHSTSRule(Rule):
    rule_id = "SEC-HSTS-001"
    category = Category.SECURITY
    severity = Severity.MEDIUM
    title = "HSTS header is missing"
    description = "The Strict-Transport-Security header is not present, so browsers are not instructed to enforce HTTPS for future requests."
    recommendation = "Configure Strict-Transport-Security header with max-age of at least 31536000 (1 year) after confirming HTTPS is correctly deployed."

    def check(self, features: FeatureVector) -> RuleResult:
        if not features.security_headers.hsts:
            finding = self._create_finding(
                MissingHSTSEvidence(
                    observed=False,
                    final_url=(
                        "https://" + features.http.server_header
                        if features.http.server_header
                        else "unknown"
                    ),
                )
            )
            return RuleResult(rule_id=self.rule_id, triggered=True, findings=[finding])
        return RuleResult(rule_id=self.rule_id, triggered=False)


class MissingCSPRule(Rule):
    rule_id = "SEC-CSP-001"
    category = Category.SECURITY
    severity = Severity.MEDIUM
    title = "Content-Security-Policy header is missing"
    description = "Without a Content-Security-Policy header, the browser cannot restrict the sources from which scripts, styles, and other resources can be loaded, increasing XSS risk."
    recommendation = "Implement a Content-Security-Policy header starting with a report-only policy, then enforce after testing."

    def check(self, features: FeatureVector) -> RuleResult:
        if not features.security_headers.csp:
            finding = self._create_finding(MissingCSPEvidence(observed=False))
            return RuleResult(rule_id=self.rule_id, triggered=True, findings=[finding])
        return RuleResult(rule_id=self.rule_id, triggered=False)


class MissingXContentTypeOptionsRule(Rule):
    rule_id = "SEC-XCTO-001"
    category = Category.SECURITY
    severity = Severity.LOW
    title = "X-Content-Type-Options header is missing"
    description = "Without X-Content-Type-Options: nosniff, browsers may MIME-sniff responses and execute content as a different type than declared."
    recommendation = "Add X-Content-Type-Options: nosniff header to all responses."

    def check(self, features: FeatureVector) -> RuleResult:
        if not features.security_headers.x_content_type_options:
            finding = self._create_finding(MissingXContentTypeOptionsEvidence(observed=False))
            return RuleResult(rule_id=self.rule_id, triggered=True, findings=[finding])
        return RuleResult(rule_id=self.rule_id, triggered=False)


class MissingXFrameOptionsRule(Rule):
    rule_id = "SEC-XFO-001"
    category = Category.SECURITY
    severity = Severity.MEDIUM
    title = "X-Frame-Options header is missing"
    description = "Without X-Frame-Options, the page can be embedded in iframes on other sites, enabling clickjacking attacks."
    recommendation = "Set X-Frame-Options: DENY or SAMEORIGIN to prevent framing."

    def check(self, features: FeatureVector) -> RuleResult:
        if not features.security_headers.x_frame_options:
            finding = self._create_finding(MissingXFrameOptionsEvidence(observed=False))
            return RuleResult(rule_id=self.rule_id, triggered=True, findings=[finding])
        return RuleResult(rule_id=self.rule_id, triggered=False)


class MissingReferrerPolicyRule(Rule):
    rule_id = "SEC-RP-001"
    category = Category.SECURITY
    severity = Severity.LOW
    title = "Referrer-Policy header is missing"
    description = "Without a Referrer-Policy, browsers may send full referrer URLs to external sites, potentially leaking sensitive information."
    recommendation = "Set Referrer-Policy: strict-origin-when-cross-origin or stricter."

    def check(self, features: FeatureVector) -> RuleResult:
        if not features.security_headers.referrer_policy:
            finding = self._create_finding(MissingReferrerPolicyEvidence(observed=False))
            return RuleResult(rule_id=self.rule_id, triggered=True, findings=[finding])
        return RuleResult(rule_id=self.rule_id, triggered=False)


class MissingPermissionsPolicyRule(Rule):
    rule_id = "SEC-PP-001"
    category = Category.SECURITY
    severity = Severity.LOW
    title = "Permissions-Policy header is missing"
    description = "Without a Permissions-Policy, the page has unrestricted access to powerful browser features like geolocation, camera, microphone."
    recommendation = "Set Permissions-Policy to restrict access to powerful features (e.g., geolocation=(), camera=(), microphone=())."

    def check(self, features: FeatureVector) -> RuleResult:
        if not features.security_headers.permissions_policy:
            finding = self._create_finding(MissingPermissionsPolicyEvidence(observed=False))
            return RuleResult(rule_id=self.rule_id, triggered=True, findings=[finding])
        return RuleResult(rule_id=self.rule_id, triggered=False)
