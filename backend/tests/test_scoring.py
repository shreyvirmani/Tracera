import pytest
from app.scoring.engine import calculate_score, get_tier, score_findings, SEVERITY_WEIGHTS, TIER_THRESHOLDS
from app.rules.engine import Finding, Severity, Category


class TestScoring:
    def test_severity_weights(self):
        assert SEVERITY_WEIGHTS[Severity.CRITICAL] == 25
        assert SEVERITY_WEIGHTS[Severity.HIGH] == 15
        assert SEVERITY_WEIGHTS[Severity.MEDIUM] == 8
        assert SEVERITY_WEIGHTS[Severity.LOW] == 3
        assert SEVERITY_WEIGHTS[Severity.INFO] == 1

    def test_calculate_score_empty(self):
        assert calculate_score([]) == 0

    def test_calculate_score_single_critical(self):
        finding = Finding(
            rule_id="TEST-001",
            category=Category.SECURITY,
            severity=Severity.CRITICAL,
            title="Test",
            description="Test",
            evidence={},
            recommendation="Test",
        )
        assert calculate_score([finding]) == 25

    def test_calculate_score_multiple(self):
        findings = [
            Finding(rule_id="1", category=Category.SECURITY, severity=Severity.CRITICAL, title="", description="", evidence={}, recommendation=""),
            Finding(rule_id="2", category=Category.SECURITY, severity=Severity.HIGH, title="", description="", evidence={}, recommendation=""),
            Finding(rule_id="3", category=Category.SECURITY, severity=Severity.MEDIUM, title="", description="", evidence={}, recommendation=""),
        ]
        assert calculate_score(findings) == 25 + 15 + 8

    def test_calculate_score_caps_at_100(self):
        findings = [Finding(rule_id=str(i), category=Category.SECURITY, severity=Severity.CRITICAL, title="", description="", evidence={}, recommendation="") for i in range(5)]
        assert calculate_score(findings) == 100

    def test_get_tier_low(self):
        assert get_tier(0) == "LOW"
        assert get_tier(24) == "LOW"

    def test_get_tier_medium(self):
        assert get_tier(25) == "MEDIUM"
        assert get_tier(49) == "MEDIUM"

    def test_get_tier_high(self):
        assert get_tier(50) == "HIGH"
        assert get_tier(74) == "HIGH"

    def test_get_tier_critical(self):
        assert get_tier(75) == "CRITICAL"
        assert get_tier(100) == "CRITICAL"

    def test_score_findings_empty(self):
        result = score_findings([])
        assert result["risk_score"] == 0
        assert result["risk_tier"] == "LOW"
        assert result["score_source"] == "fixed_baseline"
        assert result["finding_count"] == 0

    def test_score_findings_with_findings(self):
        findings = [
            Finding(rule_id="1", category=Category.SECURITY, severity=Severity.HIGH, title="", description="", evidence={}, recommendation=""),
            Finding(rule_id="2", category=Category.SECURITY, severity=Severity.MEDIUM, title="", description="", evidence={}, recommendation=""),
        ]
        result = score_findings(findings)
        assert result["risk_score"] == 23
        assert result["risk_tier"] == "LOW"
        assert result["severity_breakdown"]["high"] == 1
        assert result["severity_breakdown"]["medium"] == 1