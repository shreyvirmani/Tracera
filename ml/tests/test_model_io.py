"""
Model artifact IO tests (Phase D/F): save/load roundtrip and failure paths.
"""

import json
from pathlib import Path

import joblib
import numpy as np
import pytest
from sklearn.ensemble import IsolationForest

from ml.features.schema_v1 import MLFeaturesV1
from ml.training.model_io import (
    ALLOWED_DATA_LABELS,
    ModelArtifactError,
    ModelMetadata,
    load_model,
    save_model,
)


def tiny_model():
    X = np.random.default_rng(7).normal(size=(60, 8))
    model = IsolationForest(n_estimators=10, random_state=0).fit(X)
    return model, -0.15


def metadata(**overrides):
    base = dict(
        model_version="isoforest_test",
        model_class="IsolationForest",
        feature_schema_version="v1",
        data_label="REAL",
        data_source="common_crawl_wat",
        crawl_id="CC-MAIN-TEST",
        train_rows=60,
        unique_origins=60,
    )
    base.update(overrides)
    return ModelMetadata(**base)


class TestSaveLoadRoundtrip:
    def test_roundtrip(self, tmp_path):
        artifact = tmp_path / "artifact"
        model, threshold = tiny_model()
        save_model(model, threshold, metadata(), artifact)
        loaded_model, loaded_threshold, loaded_meta = load_model(artifact)
        assert isinstance(loaded_model, IsolationForest)
        assert loaded_threshold == threshold
        assert loaded_meta.data_label == "REAL"
        # Same scores from same inputs — reproducible inference
        X_probe = np.random.default_rng(1).normal(size=(5, 8))
        assert np.allclose(model.decision_function(X_probe), loaded_model.decision_function(X_probe))


class TestFailurePaths:
    def test_not_found(self, tmp_path):
        with pytest.raises(ModelArtifactError) as exc:
            load_model(tmp_path / "missing")
        assert exc.value.reason == "not_found"

    def test_missing_file(self, tmp_path):
        artifact = tmp_path / "artifact"
        artifact.mkdir()
        (artifact / "model_metadata.json").write_text("{}", encoding="utf-8")
        with pytest.raises(ModelArtifactError) as exc:
            load_model(artifact)
        assert exc.value.reason == "missing_file"

    def test_corrupt_model(self, tmp_path):
        artifact = tmp_path / "artifact"
        artifact.mkdir()
        (artifact / "model.joblib").write_bytes(b"not-a-joblib")
        (artifact / "threshold.json").write_text('{"anomaly_threshold": 0.1}', encoding="utf-8")
        (artifact / "model_metadata.json").write_text(
            json.dumps(metadata().to_dict()), encoding="utf-8"
        )
        with pytest.raises(ModelArtifactError) as exc:
            load_model(artifact)
        assert exc.value.reason == "corrupt"

    def test_invalid_threshold(self, tmp_path):
        artifact = tmp_path / "artifact"
        artifact.mkdir()
        model, _ = tiny_model()
        joblib.dump(model, artifact / "model.joblib")
        (artifact / "threshold.json").write_text('{"anomaly_threshold": "NaN"}', encoding="utf-8")
        (artifact / "model_metadata.json").write_text(
            json.dumps(metadata().to_dict()), encoding="utf-8"
        )
        with pytest.raises(ModelArtifactError) as exc:
            load_model(artifact)
        assert exc.value.reason == "corrupt"

    def test_schema_mismatch_rejected(self, tmp_path):
        artifact = tmp_path / "artifact"
        model, threshold = tiny_model()
        save_model(model, threshold, metadata(feature_schema_version="v2"), artifact)
        with pytest.raises(ModelArtifactError) as exc:
            load_model(artifact)
        assert exc.value.reason == "schema_mismatch"

    def test_refuses_save_without_data_label(self, tmp_path):
        model, threshold = tiny_model()
        with pytest.raises(ModelArtifactError, match="data_label"):
            save_model(model, threshold, metadata(data_label=""), tmp_path)

    def test_data_label_validation(self):
        assert "REAL" in ALLOWED_DATA_LABELS and "SYNTHETIC" in ALLOWED_DATA_LABELS


class TestFeatureSchemaLinkage:
    def test_n_features_from_schema(self, tmp_path):
        model, threshold = tiny_model()
        meta = metadata(n_features=99)
        save_model(model, threshold, meta, tmp_path)
        with pytest.raises(ModelArtifactError) as exc:
            load_model(tmp_path)
        assert exc.value.reason == "dimension_mismatch"

    def test_default_n_features_is_seventeen(self):
        assert metadata().n_features == len(MLFeaturesV1.feature_names())
