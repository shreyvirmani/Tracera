from app.features.schema import FeatureVector
from app.rules.base import Rule
from app.rules.evidence import ExcessiveResponseSizeEvidence, MixedContentEvidence
from app.rules.models import Category, RuleResult, Severity


class MixedContentRule(Rule):
    rule_id = "SEC-MIXED-001"
    category = Category.SECURITY
    severity = Severity.HIGH
    title = "Mixed content detected (HTTP resources on HTTPS page)"
    description = "The page loads resources (scripts, styles, images) over HTTP while the main page is HTTPS, undermining TLS protection."
    recommendation = "Update all resource URLs to use HTTPS or protocol-relative URLs (//)."

    def check(self, features: FeatureVector) -> RuleResult:
        if features.html.mixed_content_count > 0:
            finding = self._create_finding(
                MixedContentEvidence(
                    count=features.html.mixed_content_count,
                    resource_types=["script", "stylesheet", "image", "iframe", "form"],
                    final_url=features.http.content_type or "unknown",
                )
            )
            return RuleResult(rule_id=self.rule_id, triggered=True, findings=[finding])
        return RuleResult(rule_id=self.rule_id, triggered=False)


class ExcessiveResponseSizeRule(Rule):
    rule_id = "PERF-SIZE-001"
    category = Category.PERFORMANCE
    severity = Severity.LOW
    title = "Excessive response size"
    description = "The response size exceeds 10MB, which may indicate unnecessary data transfer or potential DoS vector."
    recommendation = "Review response content for optimization. Enable compression (gzip/br) and consider pagination for large datasets."

    def check(self, features: FeatureVector) -> RuleResult:
        threshold = 10_000_000
        if features.http.response_size_bytes > threshold:
            finding = self._create_finding(
                ExcessiveResponseSizeEvidence(
                    size_bytes=features.http.response_size_bytes,
                    threshold_bytes=threshold,
                )
            )
            return RuleResult(rule_id=self.rule_id, triggered=True, findings=[finding])
        return RuleResult(rule_id=self.rule_id, triggered=False)
