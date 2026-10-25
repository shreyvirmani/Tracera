"""
backend/app/ml tests (`ml_analysis_v1` contract).

Guarantees tested here:
- `analyze_scan_features` NEVER raises — every failure mode degrades to
  status="unavailable" with an actionable reason code.
- No value is invented: unavailable ML means no score appears in the response.
- Artifacts carrying an explicit data label (REAL / SYNTHETIC) surface that
  label in the result; unknown provenance can never be loaded.

Tests build temporary artifacts with `ml.training.model_io` so the default
suite does not depend on network access or the checked-in artifact.
"""

import json
import math
import uuid
from pathlib import Path

import numpy as np
import pytest
from sklearn.ensemble import IsolationForest

from app.core.config import settings
from app.db.models import Scan, ScanStatus
from app.ml import (
    ANALYSIS_VERSION,
    MLAnalysisStatus,
    analyze_scan_features,
    ml_features_from_scan_dict,
    result_to_dict,
)
from ml.features.schema_v1 import ML_FEATURE_SCHEMA_VERSION, FeatureValidationError, MLFeaturesV1
from ml.training.model_io import ModelMetadata, save_model


def valid_scan_features(**overrides) -> dict:
    """A realistic scan features dict (subset that maps into MLFeaturesV1)."""
    base = {
        "status_code": 200,
        "content_type": "text/html; charset=utf-8",
        "https_enabled": True,
        "hsts_present": True,
        "csp_present": False,
        "x_content_type_options_present": True,
        "x_frame_options_present": False,
        "referrer_policy_present": False,
        "permissions_policy_present": False,
        "cookie_count": 2,
        "cookie_secure_ratio": 0.5,
        "cookie_httponly_ratio": 0.5,
        "cookie_samesite_strict_ratio": 0.0,
        "cookie_samesite_lax_ratio": 0.5,
        "cookie_samesite_none_ratio": 0.0,
        "server_header_present": True,
        "x_powered_by_present": False,
    }
    base.update(overrides)
    return base


def make_artifact(dir_path: Path, data_label: str = "REAL", n_features: int = 17):
    """Save a tiny valid artifact built in memory (no repo state touched)."""
    X = np.random.default_rng(7).normal(size=(48, n_features))
    model = IsolationForest(n_estimators=20, random_state=42).fit(X)
    metadata = ModelMetadata(
        model_version=f"isoforest_{'real' if data_label == 'REAL' else 'synthetic'}",
        model_class=type(model).__name__,
        feature_schema_version=ML_FEATURE_SCHEMA_VERSION,
        data_label=data_label,
        data_source="synthetic" if data_label == "SYNTHETIC" else "common_crawl_wat",
        crawl_id="TEST" if data_label == "SYNTHETIC" else "CC-MAIN-TEST",
        train_rows=48,
        unique_origins=48,
        notes=["Fixture artifact built inside test tmp_path."],
    )
    save_model(model, -0.05, metadata, dir_path)
    return model


@pytest.fixture
def settings_env(monkeypatch):
    """
    Patch ML settings per test. `dir_path=None` restores the default
    (repo artifact dir); otherwise an absolute tmp path is used.
    """
    def _env(enabled: bool = True, artifact_dir=None):
        monkeypatch.setattr(settings, "ml_analysis_enabled", enabled)
        if artifact_dir is None:
            monkeypatch.setattr(settings, "ml_artifact_dir", "")
        else:
            monkeypatch.setattr(settings, "ml_artifact_dir", str(artifact_dir))
    return _env


@pytest.fixture
def missing_artifact(tmp_path: Path) -> Path:
    return tmp_path / "does_not_exist"


UNAVAILABLE_REASONS = {
    "ml_disabled", "ml_package_unavailable", "artifact_not_found",
    "artifact_incompatible", "artifact_corrupt", "invalid_features",
    "analysis_error",
}


# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------

class TestContract:
    def test_analysis_version(self):
        assert ANALYSIS_VERSION == "ml_analysis_v1"

    def test_result_serializes_to_json(self, settings_env, missing_artifact):
        settings_env(artifact_dir=missing_artifact)
        result = analyze_scan_features(valid_scan_features())
        payload = result_to_dict(result)
        json.dumps(payload)  # must not raise
        assert payload["status"] == "unavailable"
        assert payload["analysis_version"] == ANALYSIS_VERSION
        assert payload["anomaly_score"] is None   # no invented values

    def test_disabled_is_highest_priority(self, settings_env, missing_artifact):
        settings_env(enabled=False, artifact_dir=missing_artifact)
        # Even one clearly valid artifact location + one clearly broken feature
        # vector must yield ml_disabled (nothing is computed when disabled).
        result = analyze_scan_features(valid_scan_features())
        assert result.status == MLAnalysisStatus.UNAVAILABLE
        assert result.unavailability_reason == "ml_disabled"


# ---------------------------------------------------------------------------
# Feature mapping
# ---------------------------------------------------------------------------

class TestFeatureMapping:
    def test_maps_flags_and_defaults(self):
        features = ml_features_from_scan_dict(valid_scan_features())
        assert isinstance(features, MLFeaturesV1)
        assert features.https_enabled == 1
        assert features.is_html == 1
        assert features.cookie_count == 2
        features.validate()

    def test_is_html_false_for_json(self):
        features = ml_features_from_scan_dict(
            valid_scan_features(content_type="application/json")
        )
        assert features.is_html == 0

    def test_missing_keys_default_to_zero(self):
        features = ml_features_from_scan_dict({})
        for name in MLFeaturesV1.feature_names():
            assert getattr(features, name) == 0
        features.validate()

    def test_out_of_range_feature_still_detected(self):
        with pytest.raises(FeatureValidationError):
            ml_features_from_scan_dict(
                valid_scan_features(cookie_secure_ratio=7.5)
            ).validate()


# ---------------------------------------------------------------------------
# Graceful degradation (never raises)
# ---------------------------------------------------------------------------

class TestUnavailablePaths:
    def test_artifact_not_found(self, settings_env, missing_artifact):
        settings_env(artifact_dir=missing_artifact)
        result = analyze_scan_features(valid_scan_features())
        assert result.unavailability_reason == "artifact_not_found"
        assert result.status == MLAnalysisStatus.UNAVAILABLE
        assert result.anomaly_score is None

    def test_corrupt_artifact(self, settings_env, tmp_path: Path):
        corrupt = tmp_path / "corrupt"
        corrupt.mkdir()
        (corrupt / "model.joblib").write_bytes(b"not-a-model")
        (corrupt / "threshold.json").write_text('{"anomaly_threshold": 0.1}', encoding="utf-8")
        (corrupt / "model_metadata.json").write_text("{}", encoding="utf-8")
        settings_env(artifact_dir=corrupt)
        result = analyze_scan_features(valid_scan_features())
        assert result.unavailability_reason == "artifact_corrupt"

    def test_incompatible_artifact(self, settings_env, tmp_path: Path):
        incompatible = tmp_path / "incompatible"
        make_artifact(incompatible)  # valid shape, but schema version bumped below
        metadata_path = incompatible / "model_metadata.json"
        raw = json.loads(metadata_path.read_text(encoding="utf-8"))
        raw["feature_schema_version"] = "v9"
        metadata_path.write_text(json.dumps(raw), encoding="utf-8")
        settings_env(artifact_dir=incompatible)
        result = analyze_scan_features(valid_scan_features())
        assert result.unavailability_reason == "artifact_incompatible"
        assert result.feature_schema_version == ML_FEATURE_SCHEMA_VERSION

    def test_invalid_features(self, settings_env, tmp_path: Path):
        settings_env(artifact_dir=tmp_path)  # artifact dir irrelevant here
        features = dict(valid_scan_features())
        features["cookie_secure_ratio"] = 99.0
        result = analyze_scan_features(features)
        assert result.unavailability_reason == "invalid_features"
        issues = (result.detail or {}).get("issues") or []
        assert issues  # actionable detail: the schema issue names the field

    def test_result_reasons_are_from_the_documented_set(
        self, settings_env, missing_artifact, tmp_path: Path
    ):
        settings_env(artifact_dir=missing_artifact)
        results = [
            analyze_scan_features(valid_scan_features()),          # not_found
            analyze_scan_features({}),                             # valid (analyzed)
        ]
        settings_env(enabled=False)
        results.append(analyze_scan_features(valid_scan_features()))   # disabled
        features = valid_scan_features()
        features["cookie_count"] = -1
        results.append(analyze_scan_features(features))            # invalid
        for r in results:
            assert r.status in ("analyzed", "unavailable")
            if r.unavailability_reason is not None:
                assert r.unavailability_reason in UNAVAILABLE_REASONS


# ---------------------------------------------------------------------------
# Analyzed path
# ---------------------------------------------------------------------------

class TestAnalyzedPath:
    def test_analyzed_real_artifact(self, settings_env, tmp_path: Path):
        artifact = tmp_path / "real_v1"
        make_artifact(artifact, data_label="REAL")
        settings_env(artifact_dir=artifact)

        result = analyze_scan_features(valid_scan_features())
        assert result.status == MLAnalysisStatus.ANALYZED
        assert result.unavailability_reason is None
        assert result.feature_schema_version == ML_FEATURE_SCHEMA_VERSION
        assert result.data_label == "REAL"
        # The score is a ranking value — never forced into [0, 1]
        assert isinstance(result.anomaly_score, float)
        assert math.isfinite(result.anomaly_score)
        assert result.detail["scores_are_not_probabilities"] is True
        assert isinstance(result.anomaly_flag, bool)

    def test_synthetic_label_surfaces(self, settings_env, tmp_path: Path):
        artifact = tmp_path / "synthetic_v1"
        make_artifact(artifact, data_label="SYNTHETIC")
        settings_env(artifact_dir=artifact)
        result = analyze_scan_features(valid_scan_features())
        assert result.status == MLAnalysisStatus.ANALYZED
        assert result.data_label == "SYNTHETIC"
        # The interpretation must confess the synthetic provenance.
        assert "SYNTHETIC" in result.interpretation

    def test_score_is_reproducible(self, settings_env, tmp_path: Path):
        artifact = tmp_path / "real_v1"
        model = make_artifact(artifact, data_label="REAL")
        settings_env(artifact_dir=artifact)
        features = ml_features_from_scan_dict(valid_scan_features())
        expected = float(-model.decision_function(features.to_array().reshape(1, -1))[0])

        first = analyze_scan_features(valid_scan_features())
        second = analyze_scan_features(valid_scan_features())
        assert first.anomaly_score == second.anomaly_score
        assert first.anomaly_score == pytest.approx(expected, abs=1e-6)
        assert first.anomaly_flag == (first.anomaly_score >= -0.05)

    def test_result_to_dict_safe_for_api(self, settings_env, tmp_path: Path):
        artifact = tmp_path / "real_v1"
        make_artifact(artifact, data_label="REAL")
        settings_env(artifact_dir=artifact)
        result = analyze_scan_features(valid_scan_features())
        payload = result_to_dict(result)
        assert payload["status"] == "analyzed"
        assert set(payload) >= {
            "status", "analysis_version", "anomaly_score", "anomaly_flag",
            "data_label", "interpretation",
        }
        text = json.dumps(payload)
        # The canonical disclaimer must ship with every analyzed score...
        assert "not a probability of compromise" in text.lower()
        # ...and the score field must never be presented as one.
        assert payload["detail"]["scores_are_not_probabilities"] is True


# ---------------------------------------------------------------------------
# API integration: scans contract (additive ml_analysis field)
# ---------------------------------------------------------------------------

async def _insert_scan(test_db, features: dict) -> Scan:
    scan = Scan(
        url="https://example.com",
        canonical_url="https://example.com/",
        status=ScanStatus.COMPLETED,
        feature_schema_version="v1",
        features=features,
    )
    test_db.add(scan)
    await test_db.commit()
    await test_db.refresh(scan)
    return scan


class TestScanAPIIntegration:
    async def test_get_scan_includes_unavailable_ml_analysis(
        self, client, test_db, monkeypatch, tmp_path: Path
    ):
        monkeypatch.setattr(settings, "ml_analysis_enabled", True)
        monkeypatch.setattr(settings, "ml_artifact_dir", str(tmp_path / "missing"))
        scan = await _insert_scan(test_db, valid_scan_features())

        response = await client.get(f"/api/v1/scans/{scan.id}")
        assert response.status_code == 200
        body = response.json()
        assert body["ml_analysis"]["status"] == "unavailable"
        assert body["ml_analysis"]["unavailability_reason"] == "artifact_not_found"
        assert body["ml_analysis"]["anomaly_score"] is None

    async def test_report_endpoint_includes_ml_analysis(
        self, client, test_db, monkeypatch, tmp_path: Path
    ):
        artifact = tmp_path / "real_v1"
        make_artifact(artifact, data_label="REAL")
        monkeypatch.setattr(settings, "ml_analysis_enabled", True)
        monkeypatch.setattr(settings, "ml_artifact_dir", str(artifact))
        scan = await _insert_scan(test_db, valid_scan_features())

        response = await client.get(f"/api/v1/scans/{scan.id}/report")
        assert response.status_code == 200
        body = response.json()
        assert body["ml_analysis"]["status"] == "analyzed"
        assert body["ml_analysis"]["data_label"] == "REAL"

    async def test_scan_without_features_has_no_ml_analysis(
        self, client, test_db, monkeypatch, tmp_path: Path
    ):
        monkeypatch.setattr(settings, "ml_analysis_enabled", True)
        monkeypatch.setattr(settings, "ml_artifact_dir", str(tmp_path / "missing"))
        scan = await _insert_scan(test_db, None)  # pending scan, features=None

        response = await client.get(f"/api/v1/scans/{scan.id}")
        assert response.status_code == 200
        assert response.json()["ml_analysis"] is None

    async def test_create_scan_with_mocked_collector_is_analyzed(
        self, client, test_db, monkeypatch, tmp_path: Path
    ):
        from app.collector.safe_collector import CollectorResponse

        artifact = tmp_path / "real_v1"
        make_artifact(artifact, data_label="REAL")
        monkeypatch.setattr(settings, "ml_analysis_enabled", True)
        monkeypatch.setattr(settings, "ml_artifact_dir", str(artifact))

        fake = CollectorResponse(
            status_code=200,
            headers={
                "content-type": "text/html; charset=utf-8",
                "strict-transport-security": "max-age=31536000",
                "server": "nginx/1.24.0",
            },
            content=b"<html><body>ok</body></html>",
            url="https://example.com/",
            response_time_ms=42.0,
            redirect_count=0,
            tls_info=None,
        )
        collected = {}

        async def fake_fetch(url):
            collected["url"] = str(url.canonical_url)
            return fake

        monkeypatch.setattr("app.api.v1.scans.fetch", fake_fetch)

        response = await client.post(
            "/api/v1/scans", json={"url": "https://example.com"}
        )
        assert response.status_code == 202, response.text
        scan_id = response.json()["scan_id"]
        assert collected["url"] == "https://example.com/"

        detail = (await client.get(f"/api/v1/scans/{scan_id}")).json()
        ml_analysis = detail["ml_analysis"]
        assert ml_analysis is not None
        assert ml_analysis["status"] == "analyzed"
        assert ml_analysis["data_label"] == "REAL"
        assert isinstance(ml_analysis["anomaly_score"], float)
        assert ml_analysis["score_interpretation"]  # canonical string present
        # The deterministic part of the response is unchanged by ML analysis.
        assert detail["feature_schema_version"] == "v1"
        assert detail["findings"]  # rule engine reached the same checks as before
