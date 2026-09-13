import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.db.models import RiskTier


class SplitType(str, enum.Enum):
    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"


class DatasetVersionModel(Base):
    __tablename__ = "dataset_versions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    version = Column(String(100), nullable=False, unique=True)
    feature_schema_version = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    total_samples = Column(Integer, nullable=False, default=0)
    train_samples = Column(Integer, nullable=False, default=0)
    val_samples = Column(Integer, nullable=False, default=0)
    test_samples = Column(Integer, nullable=False, default=0)
    label_distribution = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    samples = relationship(
        "DatasetSampleModel", back_populates="dataset_version", cascade="all, delete-orphan"
    )


class DatasetSampleModel(Base):
    __tablename__ = "dataset_samples"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    dataset_version_id = Column(
        PG_UUID(as_uuid=True), ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False
    )
    feature_vector = Column(JSON, nullable=False)
    risk_tier = Column(SQLEnum(RiskTier), nullable=False)
    risk_score = Column(Integer, nullable=False)
    metadata_json = Column(JSON, nullable=False)
    split = Column(SQLEnum(SplitType), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    dataset_version = relationship("DatasetVersionModel", back_populates="samples")

    __table_args__ = (
        Index("ix_dataset_samples_version_split", "dataset_version_id", "split"),
        Index("ix_dataset_samples_tier", "risk_tier"),
    )


class ModelVersionModel(Base):
    __tablename__ = "model_versions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    model_version = Column(String(100), nullable=False, unique=True)
    dataset_version = Column(String(100), nullable=False)
    feature_schema_version = Column(String(50), nullable=False)
    algorithm = Column(String(50), nullable=False)
    hyperparameters = Column(JSON, nullable=False, default=dict)
    trained_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metrics = Column(JSON, nullable=False, default=dict)
    notes = Column(Text, nullable=True)
