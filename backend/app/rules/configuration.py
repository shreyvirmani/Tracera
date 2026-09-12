from app.features.schema import FeatureVector
from app.rules.base import Rule
from app.rules.evidence import (
    ServerVersionDisclosureEvidence,
    WildcardCORSWithCredentialsEvidence,
    XPoweredByDisclosureEvidence,
)
from app.rules.models import Category, RuleResult, Severity


class ServerVersionDisclosureRule(Rule):
    rule_id = "CFG-SERVER-001"
    category = Category.CONFIGURATION
    severity = Severity.LOW
    title = "Server version disclosed in header"
    description = "The Server header reveals specific software version information, which can help attackers target known vulnerabilities."
    recommendation = "Configure the web server to hide or genericize the Server header (e.g., 'nginx' instead of 'nginx/1.20.1')."

    def check(self, features: FeatureVector) -> RuleResult:
        server = features.http.server_header
        if server and any(c.isdigit() for c in server):
            finding = self._create_finding(ServerVersionDisclosureEvidence(value=server))
            return RuleResult(rule_id=self.rule_id, triggered=True, findings=[finding])
        return RuleResult(rule_id=self.rule_id, triggered=False)


class XPoweredByDisclosureRule(Rule):
    rule_id = "CFG-XPB-001"
    category = Category.CONFIGURATION
    severity = Severity.LOW
    title = "X-Powered-By header discloses technology"
    description = (
        "The X-Powered-By header reveals the backend technology stack, aiding reconnaissance."
    )
    recommendation = (
        "Remove or disable the X-Powered-By header in your web framework configuration."
    )

    def check(self, features: FeatureVector) -> RuleResult:
        xpb = features.http.x_powered_by
        if xpb:
            finding = self._create_finding(XPoweredByDisclosureEvidence(value=xpb))
            return RuleResult(rule_id=self.rule_id, triggered=True, findings=[finding])
        return RuleResult(rule_id=self.rule_id, triggered=False)


class WildcardCORSWithCredentialsRule(Rule):
    rule_id = "SEC-CORS-001"
    category = Category.SECURITY
    severity = Severity.HIGH
    title = "Wildcard CORS with credentials allowed"
    description = "Access-Control-Allow-Origin: * combined with Access-Control-Allow-Credentials: true violates CORS spec and exposes users to credential theft."
    recommendation = (
        "Never use wildcard origin with credentials. Specify exact allowed origins instead."
    )

    def check(self, features: FeatureVector) -> RuleResult:
        acao = getattr(features.security_headers, "access_control_allow_origin", None)
        acac = getattr(features.security_headers, "access_control_allow_credentials", None)

        if acao == "*" and acac == "true":
            finding = self._create_finding(
                WildcardCORSWithCredentialsEvidence(
                    value=acao,
                    credentials_value=acac,
                )
            )
            return RuleResult(rule_id=self.rule_id, triggered=True, findings=[finding])
        return RuleResult(rule_id=self.rule_id, triggered=False)
