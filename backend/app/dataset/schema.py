from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class LabelSource(str, Enum):
    EXPERT_REVIEW = "expert_review"
    RULE_DERIVED = "rule_derived"
    SYNTHETIC = "synthetic"
    EXTERNAL_DATASET = "external_dataset"


class RiskTier(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


SplitType = Literal["train", "validation", "test"]


class DatasetVersion(BaseModel):
    version: str
    feature_schema_version: str = "features-v1"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    description: str | None = None
    total_samples: int = 0
    train_samples: int = 0
    val_samples: int = 0
    test_samples: int = 0
    label_distribution: dict = Field(default_factory=dict)


class SampleMetadata(BaseModel):
    source_url: str | None = None
    domain: str | None = None
    synthetic_family: str | None = None
    label_source: LabelSource
    label_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    rule_ids_triggered: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DatasetSample(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    feature_vector: dict
    risk_tier: RiskTier
    risk_score: int = Field(ge=0, le=100)
    metadata: SampleMetadata
    split: SplitType | None = None


class Dataset(BaseModel):
    version: DatasetVersion
    samples: list[DatasetSample] = Field(default_factory=list)

    def add_sample(self, sample: DatasetSample) -> None:
        self.samples.append(sample)
        self.version.total_samples = len(self.samples)
        self.version.label_distribution[sample.risk_tier.value] = (
            self.version.label_distribution.get(sample.risk_tier.value, 0) + 1
        )

    def get_samples_by_split(self, split: SplitType) -> list[DatasetSample]:
        return [s for s in self.samples if s.split == split]

    def assign_splits(
        self,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        group_by: Literal["domain", "synthetic_family"] = "domain",
    ) -> None:
        import random
        from collections import defaultdict

        groups = defaultdict(list)
        for sample in self.samples:
            key = getattr(sample.metadata, group_by, "unknown")
            groups[key].append(sample)

        group_keys = list(groups.keys())
        random.shuffle(group_keys)

        n_total = len(group_keys)
        n_train = int(n_total * train_ratio)
        n_val = int(n_total * val_ratio)

        train_groups = set(group_keys[:n_train])
        val_groups = set(group_keys[n_train : n_train + n_val])

        for key, samples in groups.items():
            if key in train_groups:
                split: SplitType = "train"
            elif key in val_groups:
                split = "validation"
            else:
                split = "test"
            for sample in samples:
                sample.split = split

        self.version.train_samples = len(self.get_samples_by_split("train"))
        self.version.val_samples = len(self.get_samples_by_split("validation"))
        self.version.test_samples = len(self.get_samples_by_split("test"))
