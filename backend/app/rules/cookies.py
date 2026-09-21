from app.features.schema import FeatureVector
from app.rules.base import Rule
from app.rules.evidence import (
    InsecureCookieEvidence,
    MissingHttpOnlyEvidence,
    WeakSameSiteEvidence,
)
from app.rules.models import Category, RuleResult, Severity


class InsecureCookieRule(Rule):
    rule_id = "SEC-COOKIE-001"
    category = Category.SECURITY
    severity = Severity.HIGH
    title = "Insecure cookie (missing Secure flag)"
    description = "Cookies without the Secure flag can be transmitted over unencrypted HTTP connections, exposing session data."
    recommendation = (
        "Set the Secure flag on all cookies. Ensure the site is fully HTTPS before enabling."
    )

    def check(self, features: FeatureVector) -> RuleResult:
        findings = []
        if (
            features.cookies.total_cookies > 0
            and features.cookies.secure_cookies < features.cookies.total_cookies
        ):
            insecure_count = features.cookies.total_cookies - features.cookies.secure_cookies
            finding = self._create_finding(
                InsecureCookieEvidence(
                    cookie_name=f"{insecure_count} cookie(s) missing Secure flag",
                    secure=False,
                    httponly=features.cookies.httponly_cookies > 0,
                    samesite=None,
                )
            )
            findings.append(finding)

        return RuleResult(rule_id=self.rule_id, triggered=len(findings) > 0, findings=findings)


class MissingHttpOnlyRule(Rule):
    rule_id = "SEC-COOKIE-002"
    category = Category.SECURITY
    severity = Severity.MEDIUM
    title = "HttpOnly flag missing on cookie"
    description = "Cookies without HttpOnly are accessible via JavaScript, increasing risk of session theft via XSS."
    recommendation = "Set HttpOnly flag on all session and authentication cookies."

    def check(self, features: FeatureVector) -> RuleResult:
        findings = []
        if (
            features.cookies.total_cookies > 0
            and features.cookies.httponly_cookies < features.cookies.total_cookies
        ):
            missing_httponly = features.cookies.total_cookies - features.cookies.httponly_cookies
            finding = self._create_finding(
                MissingHttpOnlyEvidence(
                    cookie_name=f"{missing_httponly} cookie(s) missing HttpOnly",
                    httponly=False,
                    secure=features.cookies.secure_cookies > 0,
                )
            )
            findings.append(finding)

        return RuleResult(rule_id=self.rule_id, triggered=len(findings) > 0, findings=findings)


class WeakSameSiteRule(Rule):
    rule_id = "SEC-COOKIE-003"
    category = Category.SECURITY
    severity = Severity.MEDIUM
    title = "SameSite attribute missing or weak"
    description = (
        "Cookies without SameSite (or set to None without Secure) are vulnerable to CSRF attacks."
    )
    recommendation = "Set SameSite=Lax for most cookies, SameSite=Strict for sensitive operations, or SameSite=None; Secure for cross-site cookies."

    def check(self, features: FeatureVector) -> RuleResult:
        findings = []
        if (
            features.cookies.total_cookies > 0
            and features.cookies.samesite_cookies < features.cookies.total_cookies
        ):
            missing_samesite = features.cookies.total_cookies - features.cookies.samesite_cookies
            finding = self._create_finding(
                WeakSameSiteEvidence(
                    cookie_name=f"{missing_samesite} cookie(s) missing/weak SameSite",
                    samesite=None,
                )
            )
            findings.append(finding)

        return RuleResult(rule_id=self.rule_id, triggered=len(findings) > 0, findings=findings)
