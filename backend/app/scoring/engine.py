from typing import List
from app.rules.engine import Finding, Severity


SEVERITY_WEIGHTS = {
    Severity.CRITICAL: 25,
    Severity.HIGH: 15,
    Severity.MEDIUM: 8,
    Severity.LOW: 3,
    Severity.INFO: 1,
}


TIER_THRESHOLDS = {
    "LOW": (0, 24),
    "MEDIUM": (25, 49),
    "HIGH": (50, 74),
    "CRITICAL": (75, 100),
}


def calculate_score(findings: List[Finding]) -> int:
    raw_score = sum(SEVERITY_WEIGHTS.get(f.severity, 0) for f in findings)
    return min(100, raw_score)


def get_tier(score: int) -> str:
    for tier, (low, high) in TIER_THRESHOLDS.items():
        if low <= score <= high:
            return tier
    return "CRITICAL"


def score_findings(findings: List[Finding]) -> dict:
    score = calculate_score(findings)
    tier = get_tier(score)
    return {
        "risk_score": score,
        "risk_tier": tier,
        "score_source": "fixed_baseline",
        "finding_count": len(findings),
        "severity_breakdown": {
            "critical": sum(1 for f in findings if f.severity == Severity.CRITICAL),
            "high": sum(1 for f in findings if f.severity == Severity.HIGH),
            "medium": sum(1 for f in findings if f.severity == Severity.MEDIUM),
            "low": sum(1 for f in findings if f.severity == Severity.LOW),
            "info": sum(1 for f in findings if f.severity == Severity.INFO),
        },
    }