"""
Model artifact save/load for Tracera ML.

An artifact is a directory containing:
- `model.joblib`          — the trained sklearn model (deterministic given seed)
- `threshold.json`        — {"anomaly_threshold": float, "method": "train P5 of decision_function"}
- `model_metadata.json`   — provenance (versions, data label, config, training stats)

Loading validates:
- both files exist and parse,
- feature schema version compatibility with the current code,
- data label is explicitly REAL or SYNTHETIC (never absent),
- dimensionality matches MLFeaturesV1 (17).

Raises `ModelArtifactError` with a specific reason on any failure — callers
(_backend/app/ml, evaluation) must degrade gracefully rather than crash.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
import numpy as np

from ml.features.schema_v1 import (
    ML_FEATURE_SCHEMA_VERSION,
    MLFeaturesV1,
)

MODEL_FORMAT_VERSION = 1
ALLOWED_DATA_LABELS = ("REAL", "SYNTHETIC")


class ModelArtifactError(Exception):
    """Raised when a model artifact is missing, corrupt, or incompatible."""

    def __init__(self, reason: str, detail: str = ""):
        super().__init__(reason if not detail else f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


@dataclass
class ModelMetadata:
    """Provenance and configuration of one trained model artifact."""
    model_version: str
    model_class: str
    feature_schema_version: str
    data_label: str                       # REAL or SYNTHETIC — required!
    data_source: str                      # e.g. "common_crawl_wat", "synthetic"
    crawl_id: str = ""
    trained_at: str = ""
    train_rows: int = 0
    unique_origins: int = 0
    n_features: int = len(MLFeaturesV1.feature_names())
    params: Dict[str, Any] = field(default_factory=dict)
    seeds: List[int] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    model_format_version: int = MODEL_FORMAT_VERSION

    def to_dict(self) -> dict:
        return asdict(self)

    def validate(self) -> None:
        if self.feature_schema_version != ML_FEATURE_SCHEMA_VERSION:
            raise ModelArtifactError(
                "schema_mismatch",
                f"artifact trained with feature schema {self.feature_schema_version!r} "
                f"but this code expects {ML_FEATURE_SCHEMA_VERSION!r}",
            )
        if self.data_label not in ALLOWED_DATA_LABELS:
            raise ModelArtifactError(
                "missing_data_label",
                f"artifact metadata must carry an explicit data_label in {ALLOWED_DATA_LABELS}; "
                f"got {self.data_label!r}",
            )
        if self.n_features != len(MLFeaturesV1.feature_names()):
            raise ModelArtifactError(
                "dimension_mismatch",
                f"artifact expects {self.n_features} features; schema defines "
                f"{len(MLFeaturesV1.feature_names())}",
            )


def save_model(
    model: Any,
    threshold: float,
    metadata: ModelMetadata,
    artifact_dir: Path,
) -> Path:
    """Persist model + threshold + metadata (atomic-ish: write then rename)."""
    artifact_dir = Path(artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    if metadata.data_label not in ALLOWED_DATA_LABELS:
        raise ModelArtifactError(
            "missing_data_label",
            f"refusing to save artifact without explicit data_label; got {metadata.data_label!r}",
        )
    if not metadata.trained_at:
        metadata.trained_at = datetime.now(timezone.utc).isoformat()

    joblib.dump(model, artifact_dir / "model.joblib")
    (artifact_dir / "threshold.json").write_text(
        json.dumps({"anomaly_threshold": float(threshold), "method": "percentile_5_of_train_decision_function"}),
        encoding="utf-8",
    )
    (artifact_dir / "model_metadata.json").write_text(
        json.dumps(metadata.to_dict(), indent=2), encoding="utf-8"
    )
    return artifact_dir


def load_model(artifact_dir: Path) -> Tuple[Any, float, ModelMetadata]:
    """
    Load and validate a model artifact.

    Returns (model, threshold, metadata). Raises ModelArtifactError with one of:
    'not_found', 'missing_file', 'corrupt', 'schema_mismatch',
    'missing_data_label', 'dimension_mismatch', 'invalid_threshold'.
    """
    artifact_dir = Path(artifact_dir)
    if not artifact_dir.is_dir():
        raise ModelArtifactError(
            "not_found",
            f"artifact directory does not exist: {artifact_dir}. Train and save a "
            "model first (python ml/training/evaluate.py).",
        )
    model_path = artifact_dir / "model.joblib"
    threshold_path = artifact_dir / "threshold.json"
    metadata_path = artifact_dir / "model_metadata.json"
    for p in (model_path, threshold_path, metadata_path):
        if not p.exists():
            raise ModelArtifactError(
                "missing_file",
                f"artifact directory {artifact_dir} is incomplete: {p.name} is missing",
            )

    try:
        model = joblib.load(model_path)
    except Exception as e:
        raise ModelArtifactError("corrupt", f"failed to load {model_path}: {e}") from e

    try:
        threshold_data = json.loads(threshold_path.read_text(encoding="utf-8"))
        threshold = float(threshold_data["anomaly_threshold"])
        if not np.isfinite(threshold):
            raise ValueError("threshold is not finite")
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        raise ModelArtifactError("corrupt", f"invalid {threshold_path.name}: {e}") from e

    try:
        metadata = ModelMetadata(**json.loads(metadata_path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, TypeError) as e:
        raise ModelArtifactError("corrupt", f"invalid {metadata_path.name}: {e}") from e
    metadata.validate()
    return model, threshold, metadata
