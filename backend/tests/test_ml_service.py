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

from datetime import UTC, datetime
import json
import math
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
import numpy as np
import pytest
from sklearn.ensemble import IsolationForest

from app.core.config import settings
from app.db.models import Scan, ScanStatus
from app.main import app
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


def make_artifact(
    out_dir: Path,
    data_label: str = "REAL",
    train_rows: int = 100,
    model_version: str = "isoforest_v1",
) -> None:
    rng = np.random.default_rng(42)
    X = rng.normal(size=(train_rows, 17))
    model = IsolationForest(n_estimators=10, random_state=42)
    model.fit(X)
    meta = ModelMetadata(
        model_version=model_version,
        model_class="IsolationForest",
        feature_schema_version="v1",
        data_label=data_label,
        data_source="test",
        train_rows=train_rows,
    )
    save_model(model=model, metadata=meta, threshold=0.05, output_dir=out_dir)


# ---------------------------------------------------------------------------
# Feature mapping tests
# ---------------------------------------------------------------------------

class TestFeatureMapping:
    def test_maps_clean_dict(self):
        f = ml_features_from_scan_dict(valid_scan_features())
        assert isinstance(f, MLFeaturesV1)
        assert f.status_code == 200
        assert f.is_html == 1
        assert f.https_enabled == 1
        assert f.hsts_present == 1
        assert f.cookie_count == 2
        assert f.cookie_secure_ratio == 0.5

    def test_derives_is_html_false_for_non_html(self):
        f = ml_features_from_scan_dict(valid_scan_features(content_type="application/json"))
        assert f.is_html == 0

    def test_missing_fields_default_gracefully(self):
        f = ml_features_from_scan_dict({})
        assert f.status_code == 0
        assert f.https_enabled == 0
        assert f.cookie_count == 0
        assert f.is_html == 0


# ---------------------------------------------------------------------------
# analyze_scan_features guarantees: total graceful degradation
# ---------------------------------------------------------------------------

class TestServiceGracefulDegradation:
    def test_disabled_by_config(self, tmp_path: Path):
        res = analyze_scan_features(valid_scan_features(), enabled=False)
        assert res.status == MLAnalysisStatus.UNAVAILABLE
        assert res.unavailability_reason == "ml_disabled"
        assert res.anomaly_score is None
        assert "disabled" in res.interpretation.lower()

    def test_artifact_not_found(self, monkeypatch, tmp_path: Path):
        monkeypatch.setattr(settings, "ml_artifact_dir", str(tmp_path / "nonexistent"))
        res = analyze_scan_features(valid_scan_features(), enabled=True)
        assert res.status == MLAnalysisStatus.UNAVAILABLE
        assert res.unavailability_reason == "artifact_not_found"
        assert res.anomaly_score is None

    def test_corrupt_artifact_metadata(self, monkeypatch, tmp_path: Path):
        art_dir = tmp_path / "corrupt"
        make_artifact(art_dir)
        (art_dir / "model_metadata.json").write_text("{not-valid-json", encoding="utf-8")
        monkeypatch.setattr(settings, "ml_artifact_dir", str(art_dir))

        res = analyze_scan_features(valid_scan_features(), enabled=True)
        assert res.status == MLAnalysisStatus.UNAVAILABLE
        assert res.unavailability_reason == "artifact_corrupt"
        assert res.anomaly_score is None

    def test_unknown_provenance_refused_at_inference(self, monkeypatch, tmp_path: Path):
        """Even if someone bypassed the save guard, loading UNKNOWN data must fail."""
        art_dir = tmp_path / "unknown_prov"
        make_artifact(art_dir)
        meta_path = art_dir / "model_metadata.json"
        raw = json.loads(meta_path.read_text(encoding="utf-8"))
        raw["data_label"] = "UNKNOWN"
        meta_path.write_text(json.dumps(raw), encoding="utf-8")
        monkeypatch.setattr(settings, "ml_artifact_dir", str(art_dir))

        res = analyze_scan_features(valid_scan_features(), enabled=True)
        assert res.status == MLAnalysisStatus.UNAVAILABLE
        assert res.unavailability_reason == "artifact_corrupt"
        assert res.anomaly_score is None

    def test_incompatible_feature_schema_refused(self, monkeypatch, tmp_path: Path):
        art_dir = tmp_path / "incompatible"
        make_artifact(art_dir)
        meta_path = art_dir / "model_metadata.json"
        raw = json.loads(meta_path.read_text(encoding="utf-8"))
        raw["feature_schema_version"] = "v999_future"
        meta_path.write_text(json.dumps(raw), encoding="utf-8")
        monkeypatch.setattr(settings, "ml_artifact_dir", str(art_dir))

        res = analyze_scan_features(valid_scan_features(), enabled=True)
        assert res.status == MLAnalysisStatus.UNAVAILABLE
        assert res.unavailability_reason == "artifact_incompatible"
        assert res.anomaly_score is None

    def test_dimension_mismatch_refused(self, monkeypatch, tmp_path: Path):
        art_dir = tmp_path / "dim_mismatch"
        make_artifact(art_dir)
        meta_path = art_dir / "model_metadata.json"
        raw = json.loads(meta_path.read_text(encoding="utf-8"))
        raw["expected_features"] = 16  # trained with 17
        meta_path.write_text(json.dumps(raw), encoding="utf-8")
        monkeypatch.setattr(settings, "ml_artifact_dir", str(art_dir))

        res = analyze_scan_features(valid_scan_features(), enabled=True)
        assert res.status == MLAnalysisStatus.UNAVAILABLE
        assert res.unavailability_reason == "artifact_incompatible"

    def test_invalid_features_yields_reason(self, monkeypatch, tmp_path: Path):
        art_dir = tmp_path / "valid"
        make_artifact(art_dir)
        monkeypatch.setattr(settings, "ml_artifact_dir", str(art_dir))

        # ratio > 1.0 violates MLFeaturesV1 validator
        bad = valid_scan_features(cookie_secure_ratio=5.0)
        res = analyze_scan_features(bad, enabled=True)
        assert res.status == MLAnalysisStatus.UNAVAILABLE
        assert res.unavailability_reason == "invalid_features"
        assert res.detail["stage"] == "feature_mapping_or_validation"

    def test_negative_values_rejected(self, monkeypatch, tmp_path: Path):
        art_dir = tmp_path / "valid"
        make_artifact(art_dir)
        monkeypatch.setattr(settings, "ml_artifact_dir", str(art_dir))

        bad = valid_scan_features(cookie_count=-3)
        res = analyze_scan_features(bad, enabled=True)
        assert res.status == MLAnalysisStatus.UNAVAILABLE
        assert res.unavailability_reason == "invalid_features"

    def test_nan_values_rejected(self, monkeypatch, tmp_path: Path):
        art_dir = tmp_path / "valid"
        make_artifact(art_dir)
        monkeypatch.setattr(settings, "ml_artifact_dir", str(art_dir))

        bad = valid_scan_features(cookie_secure_ratio=float("nan"))
        res = analyze_scan_features(bad, enabled=True)
        assert res.status == MLAnalysisStatus.UNAVAILABLE
        assert res.unavailability_reason == "invalid_features"

    def test_non_dict_features_handled(self, monkeypatch, tmp_path: Path):
        art_dir = tmp_path / "valid"
        make_artifact(art_dir)
        monkeypatch.setattr(settings, "ml_artifact_dir", str(art_dir))

        res = analyze_scan_features("not-a-dict", enabled=True)  # type: ignore
        assert res.status == MLAnalysisStatus.UNAVAILABLE
        assert res.unavailability_reason == "invalid_features"


# ---------------------------------------------------------------------------
# Successful inference: contract guarantees
# ---------------------------------------------------------------------------

class TestServiceSuccessContract:
    def test_analyzed_with_real_data_label(self, monkeypatch, tmp_path: Path):
        art_dir = tmp_path / "real_art"
        make_artifact(art_dir, data_label="REAL", model_version="isoforest_test_v1")
        monkeypatch.setattr(settings, "ml_artifact_dir", str(art_dir))

        res = analyze_scan_features(valid_scan_features(), enabled=True)
        assert res.status == MLAnalysisStatus.ANALYZED
        assert res.data_label == "REAL"
        assert res.model_version == "isoforest_test_v1"
        assert res.feature_schema_version == "v1"
        assert isinstance(res.anomaly_score, float)
        assert isinstance(res.anomaly_flag, bool)
        assert res.anomaly_score is not None
        assert not math.isnan(res.anomaly_score)
        assert "not a probability of compromise" in res.score_interpretation.lower()
        assert "trained on real data" in res.interpretation.lower()
        assert res.detail["scores_are_not_probabilities"] is True

    def test_analyzed_with_synthetic_data_label(self, monkeypatch, tmp_path: Path):
        art_dir = tmp_path / "synth_art"
        make_artifact(art_dir, data_label="SYNTHETIC")
        monkeypatch.setattr(settings, "ml_artifact_dir", str(art_dir))

        res = analyze_scan_features(valid_scan_features(), enabled=True)
        assert res.status == MLAnalysisStatus.ANALYZED
        assert res.data_label == "SYNTHETIC"
        assert "trained on synthetic data" in res.interpretation.lower()

    def test_higher_score_is_more_anomalous(self, monkeypatch, tmp_path: Path):
        """
        Verify the polarity convention: raw sklearn decision_function is
        higher = more normal; we negate so HIGHER = MORE ANOMALOUS.
        """
        art_dir = tmp_path / "art"
        # Train on clusters of 0s
        rng = np.random.default_rng(0)
        X = rng.normal(loc=0.0, scale=0.1, size=(200, 17))
        model = IsolationForest(n_estimators=20, random_state=0).fit(X)
        meta = ModelMetadata(
            model_version="isoforest_test",
            model_class="IsolationForest",
            feature_schema_version="v1",
            data_label="REAL",
            data_source="test",
            train_rows=200,
        )
        save_model(model, meta, threshold=0.0, output_dir=art_dir)
        monkeypatch.setattr(settings, "ml_artifact_dir", str(art_dir))

        normal = valid_scan_features()
        # Typical values near the training center
        res_normal = analyze_scan_features(normal, enabled=True)

        # Extreme outlier feature vector
        outlier = valid_scan_features(
            status_code=503,
            cookie_count=200,
            cookie_secure_ratio=0.0,
            cookie_httponly_ratio=0.0,
        )
        res_outlier = analyze_scan_features(outlier, enabled=True)

        assert res_outlier.anomaly_score > res_normal.anomaly_score

    def test_result_to_dict_is_json_safe(self, monkeypatch, tmp_path: Path):
        art_dir = tmp_path / "art"
        make_artifact(art_dir, data_label="REAL")
        monkeypatch.setattr(settings, "ml_artifact_dir", str(art_dir))

        res = analyze_scan_features(valid_scan_features(), enabled=True)
        payload = result_to_dict(res)
        assert isinstance(payload, dict)
        assert set(payload.keys()) >= {
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

class TestScanAPIIntegration:
    def test_get_scan_includes_unavailable_ml_analysis(self, monkeypatch, tmp_path: Path):
        client = TestClient(app)
        monkeypatch.setattr(settings, "ml_analysis_enabled", True)
        monkeypatch.setattr(settings, "ml_artifact_dir", str(tmp_path / "missing"))
        scan_id = uuid.uuid4()
        fake_scan = Scan(
            id=scan_id,
            url="https://example.com",
            canonical_url="https://example.com/",
            status=ScanStatus.COMPLETED,
            feature_schema_version="features-v1",
            features=valid_scan_features(),
            created_at=datetime.now(UTC),
        )
        fake_scan.findings = []

        async def fake_get_scan(db, sid):
            return fake_scan

        monkeypatch.setattr("app.api.v1.scans.get_scan", fake_get_scan)

        response = client.get(f"/api/v1/scans/{scan_id}")
        assert response.status_code == 200
        body = response.json()
        assert body["ml_analysis"]["status"] == "unavailable"
        assert body["ml_analysis"]["unavailability_reason"] == "artifact_not_found"
        assert body["ml_analysis"]["anomaly_score"] is None

    def test_report_endpoint_includes_ml_analysis(self, monkeypatch, tmp_path: Path):
        client = TestClient(app)
        artifact = tmp_path / "real_v1"
        make_artifact(artifact, data_label="REAL")
        monkeypatch.setattr(settings, "ml_analysis_enabled", True)
        monkeypatch.setattr(settings, "ml_artifact_dir", str(artifact))
        scan_id = uuid.uuid4()
        fake_scan = Scan(
            id=scan_id,
            url="https://example.com",
            canonical_url="https://example.com/",
            status=ScanStatus.COMPLETED,
            feature_schema_version="features-v1",
            features=valid_scan_features(),
            created_at=datetime.now(UTC),
        )
        fake_scan.findings = []

        async def fake_get_scan(db, sid):
            return fake_scan

        monkeypatch.setattr("app.api.v1.scans.get_scan", fake_get_scan)

        response = client.get(f"/api/v1/scans/{scan_id}/report")
        assert response.status_code == 200
        body = response.json()
        assert body["ml_analysis"]["status"] == "analyzed"
        assert body["ml_analysis"]["data_label"] == "REAL"

    def test_scan_without_features_has_no_ml_analysis(self, monkeypatch, tmp_path: Path):
        client = TestClient(app)
        monkeypatch.setattr(settings, "ml_analysis_enabled", True)
        monkeypatch.setattr(settings, "ml_artifact_dir", str(tmp_path / "missing"))
        scan_id = uuid.uuid4()
        fake_scan = Scan(
            id=scan_id,
            url="https://example.com",
            canonical_url="https://example.com/",
            status=ScanStatus.COMPLETED,
            feature_schema_version="features-v1",
            features=None,
            created_at=datetime.now(UTC),
        )
        fake_scan.findings = []

        async def fake_get_scan(db, sid):
            return fake_scan

        monkeypatch.setattr("app.api.v1.scans.get_scan", fake_get_scan)

        response = client.get(f"/api/v1/scans/{scan_id}")
        assert response.status_code == 200
        assert response.json()["ml_analysis"] is None

    def test_create_scan_with_mocked_collector_is_analyzed(self, monkeypatch, tmp_path: Path):
        from app.collector.collector import CollectorResponse
        from app.core.ssrf_guard import ResolvedIP

        client = TestClient(app)
        artifact = tmp_path / "real_v1"
        make_artifact(artifact, data_label="REAL")
        monkeypatch.setattr(settings, "ml_analysis_enabled", True)
        monkeypatch.setattr(settings, "ml_artifact_dir", str(artifact))

        monkeypatch.setattr(
            "app.api.v1.scans.check_ssrf",
            lambda url: ResolvedIP("93.184.216.34", 4, False, False, False, False, False),
        )

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

        async def fake_collect(*args, **kwargs):
            return fake

        scan_id = uuid.uuid4()
        created_scan = Scan(
            id=scan_id,
            url="https://example.com",
            canonical_url="https://example.com/",
            status=ScanStatus.COMPLETED,
            feature_schema_version="features-v1",
            features=valid_scan_features(),
            created_at=datetime.now(UTC),
        )
        created_scan.findings = []

        async def fake_create_scan(db, url, canonical_url, feature_schema_version, features=None):
            return created_scan

        async def fake_update_scan_completed(db, scan_id, status, **kwargs):
            return created_scan

        async def fake_get_scan(db, sid):
            return created_scan

        monkeypatch.setattr("app.api.v1.scans.collect", fake_collect)
        monkeypatch.setattr("app.api.v1.scans.create_scan", fake_create_scan)
        monkeypatch.setattr("app.api.v1.scans.update_scan_completed", fake_update_scan_completed)
        monkeypatch.setattr("app.api.v1.scans.get_scan", fake_get_scan)

        response = client.post(
            "/api/v1/scans", json={"url": "https://example.com"}
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["scan_id"] == str(scan_id)
        assert data["status"] == "completed"
        ml_analysis = data["ml_analysis"]
        assert ml_analysis is not None
        assert ml_analysis["status"] == "analyzed"
        assert ml_analysis["data_label"] == "REAL"
        assert isinstance(ml_analysis["anomaly_score"], float)
        assert ml_analysis["score_interpretation"]
