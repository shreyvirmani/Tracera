import numpy as np

from app.features.schema import FeatureVector
from app.rules import registry
from app.scoring.risk import calculate_risk_score, determine_risk_tier


class FixedBaseline:
    """
    Fixed baseline risk scoring using deterministic rules.
    This is the transparent, rule-based baseline that ML models must beat.
    """

    def __init__(self):
        self.name = "fixed_baseline"
        self.version = "1.0"

    def predict_proba(self, features: FeatureVector) -> np.ndarray:
        """Predict probability distribution over risk tiers."""
        risk_score = self._calculate_score(features)
        risk_tier = determine_risk_tier(risk_score)

        # Return one-hot encoded probability
        tiers = ["low", "medium", "high", "critical"]
        proba = np.zeros(4)
        proba[tiers.index(risk_tier)] = 1.0
        return proba

    def predict(self, features: FeatureVector) -> str:
        """Predict risk tier label."""
        risk_score = self._calculate_score(features)
        return determine_risk_tier(risk_score)

    def predict_score(self, features: FeatureVector) -> int:
        """Predict continuous risk score 0-100."""
        return self._calculate_score(features)

    def _calculate_score(self, features: FeatureVector) -> int:
        rule_results = registry.run_all(features)
        findings = []
        for result in rule_results:
            if result.triggered:
                findings.extend(result.findings)
        return calculate_risk_score(findings)

    def get_metadata(self) -> dict:
        return {
            "model_name": self.name,
            "model_version": self.version,
            "model_type": "fixed_baseline",
        }
