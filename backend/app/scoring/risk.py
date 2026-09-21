from app.rules.models import Category, DetectionSource, Severity

SEVERITY_WEIGHTS = {
    Severity.CRITICAL: 25,
    Severity.HIGH: 15,
    Severity.MEDIUM: 10,
    Severity.LOW: 5,
    Severity.INFO: 1,
}


def calculate_risk_score(findings: list) -> int:
    total = sum(SEVERITY_WEIGHTS.get(f.severity, 0) for f in findings)
    return min(total, 100)


def determine_risk_tier(score: int) -> str:
    if score >= 75:
        return "critical"
    elif score >= 50:
        return "high"
    elif score >= 25:
        return "medium"
    else:
        return "low"


def map_severity(severity: Severity) -> str:
    mapping = {
        Severity.CRITICAL: "critical",
        Severity.HIGH: "high",
        Severity.MEDIUM: "medium",
        Severity.LOW: "low",
        Severity.INFO: "info",
    }
    return mapping.get(severity, "info")


def map_category(category: Category) -> str:
    mapping = {
        Category.SECURITY: "security",
        Category.CONFIGURATION: "configuration",
        Category.PERFORMANCE: "performance",
        Category.PRIVACY: "privacy",
    }
    return mapping.get(category, "security")


def map_source(source: DetectionSource) -> str:
    mapping = {
        DetectionSource.RULE_ENGINE: "rule_engine",
        DetectionSource.ML_MODEL: "ml_model",
        DetectionSource.CVE_CORRELATOR: "cve_correlator",
    }
    return mapping.get(source, "rule_engine")
