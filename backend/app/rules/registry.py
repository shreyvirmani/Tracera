from app.features.schema import FeatureVector
from app.rules.base import Rule
from app.rules.models import RuleResult


class RuleRegistry:
    def __init__(self):
        self._rules: list[Rule] = []

    def register(self, rule: Rule) -> None:
        self._rules.append(rule)

    def get_all(self) -> list[Rule]:
        return self._rules.copy()

    def get_by_id(self, rule_id: str) -> Rule | None:
        for rule in self._rules:
            if rule.rule_id == rule_id:
                return rule
        return None

    def get_by_category(self, category) -> list[Rule]:
        return [r for r in self._rules if r.category == category]

    def run_all(self, features: FeatureVector) -> list[RuleResult]:
        results = []
        for rule in self._rules:
            try:
                result = rule.check(features)
                results.append(result)
            except Exception as e:
                results.append(
                    RuleResult(
                        rule_id=rule.rule_id,
                        triggered=False,
                        metadata={"error": str(e)},
                    )
                )
        return results


registry = RuleRegistry()
