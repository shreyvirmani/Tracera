import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from uuid import UUID, uuid4


class Algorithm(str, Enum):
    LOGISTIC_REGRESSION = "logistic_regression"
    RANDOM_FOREST = "random_forest"
    XGBOOST = "xgboost"
    FIXED_BASELINE = "fixed_baseline"


@dataclass
class ExperimentRecord:
    experiment_id: UUID = field(default_factory=uuid4)
    model_name: str = ""
    model_version: str = ""
    algorithm: Algorithm = Algorithm.LOGISTIC_REGRESSION
    dataset_version: str = ""
    feature_schema_version: str = "features-v1"
    hyperparameters: dict = field(default_factory=dict)
    trained_at: datetime = field(default_factory=datetime.utcnow)
    metrics: dict = field(default_factory=dict)
    notes: str = ""
    artifact_path: str = ""
    git_commit: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        data["experiment_id"] = str(data["experiment_id"])
        data["algorithm"] = data["algorithm"].value
        data["trained_at"] = data["trained_at"].isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "ExperimentRecord":
        data = data.copy()
        data["experiment_id"] = UUID(data["experiment_id"])
        data["algorithm"] = Algorithm(data["algorithm"])
        data["trained_at"] = datetime.fromisoformat(data["trained_at"])
        return cls(**data)


class ExperimentTracker:
    """Track ML experiments with versioned metadata."""

    def __init__(self, storage_path: str = "ml/experiments"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.index_path = self.storage_path / "index.json"
        self._load_index()

    def _load_index(self) -> None:
        if self.index_path.exists():
            with open(self.index_path) as f:
                self.index = json.load(f)
        else:
            self.index = []

    def _save_index(self) -> None:
        with open(self.index_path, "w") as f:
            json.dump(self.index, f, indent=2)

    def log_experiment(self, record: ExperimentRecord) -> None:
        self.index.append(record.to_dict())
        self._save_index()

    def get_experiments(
        self,
        dataset_version: str | None = None,
        algorithm: str | None = None,
    ) -> list[ExperimentRecord]:
        results = []
        for exp in self.index:
            if dataset_version and exp["dataset_version"] != dataset_version:
                continue
            if algorithm and exp["algorithm"] != algorithm:
                continue
            results.append(ExperimentRecord.from_dict(exp))
        return results

    def get_best_experiment(
        self,
        dataset_version: str,
        metric: str = "macro_f1",
    ) -> ExperimentRecord | None:
        experiments = self.get_experiments(dataset_version=dataset_version)
        if not experiments:
            return None

        def get_metric(exp: ExperimentRecord) -> float:
            return exp.metrics.get(metric, 0.0)

        return max(experiments, key=get_metric)
