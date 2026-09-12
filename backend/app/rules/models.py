from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Category(str, Enum):
    SECURITY = "security"
    CONFIGURATION = "configuration"
    PERFORMANCE = "performance"
    PRIVACY = "privacy"


class DetectionSource(str, Enum):
    RULE_ENGINE = "rule_engine"
    ML_MODEL = "ml_model"
    CVE_CORRELATOR = "cve_correlator"


class FindingEvidence(BaseModel):
    pass


class Finding(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    rule_id: str
    category: Category
    severity: Severity
    title: str
    description: str
    evidence: FindingEvidence
    recommendation: str
    source: DetectionSource = DetectionSource.RULE_ENGINE
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RuleResult(BaseModel):
    rule_id: str
    triggered: bool
    findings: list[Finding] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
