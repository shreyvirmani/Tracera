from abc import ABC, abstractmethod

from app.features.schema import FeatureVector
from app.rules.models import Category, Finding, FindingEvidence, RuleResult, Severity


class Rule(ABC):
    rule_id: str
    category: Category
    severity: Severity
    title: str
    description: str
    recommendation: str

    @abstractmethod
    def check(self, features: FeatureVector) -> RuleResult:
        pass

    def _create_finding(
        self,
        evidence: FindingEvidence,
        severity: Severity | None = None,
        confidence: float = 1.0,
    ) -> Finding:
        return Finding(
            rule_id=self.rule_id,
            category=self.category,
            severity=severity or self.severity,
            title=self.title,
            description=self.description,
            evidence=evidence,
            recommendation=self.recommendation,
            confidence=confidence,
        )
