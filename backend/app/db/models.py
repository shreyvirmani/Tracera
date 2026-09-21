import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class ScanStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class RiskTier(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ScoreSource(str, enum.Enum):
    FIXED_BASELINE = "fixed_baseline"
    ML_MODEL = "ml_model"
    FALLBACK_BASELINE = "fallback_baseline"


class FindingSeverity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingCategory(str, enum.Enum):
    SECURITY = "security"
    CONFIGURATION = "configuration"
    PERFORMANCE = "performance"
    PRIVACY = "privacy"


class DetectionSource(str, enum.Enum):
    RULE_ENGINE = "rule_engine"
    ML_MODEL = "ml_model"
    CVE_CORRELATOR = "cve_correlator"


class Scan(Base):
    __tablename__ = "scans"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = Column(Text, nullable=False)
    canonical_url = Column(Text, nullable=False)
    status = Column(SQLEnum(ScanStatus), nullable=False, default=ScanStatus.PENDING)
    feature_schema_version = Column(String(50), nullable=False)
    risk_score = Column(Integer, nullable=True)
    risk_tier = Column(SQLEnum(RiskTier), nullable=True)
    score_source = Column(SQLEnum(ScoreSource), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_code = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)

    findings = relationship("Finding", back_populates="scan", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_scans_created_at", "created_at"),
        Index("ix_scans_status", "status"),
    )


class Finding(Base):
    __tablename__ = "findings"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(
        PG_UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False
    )
    rule_id = Column(String(100), nullable=False)
    category = Column(SQLEnum(FindingCategory), nullable=False)
    severity = Column(SQLEnum(FindingSeverity), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    evidence_json = Column(JSON, nullable=False, default=dict)
    recommendation = Column(Text, nullable=False)
    source = Column(SQLEnum(DetectionSource), nullable=False, default=DetectionSource.RULE_ENGINE)
    confidence = Column(Integer, nullable=False, default=100)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    scan = relationship("Scan", back_populates="findings")

    __table_args__ = (
        Index("ix_findings_scan_id", "scan_id"),
        Index("ix_findings_rule_id", "rule_id"),
        Index("ix_findings_severity", "severity"),
    )