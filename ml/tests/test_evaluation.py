"""
Evaluation framework tests (Phase D/F).

The default test suite runs WITHOUT network access. Datasets used here are a
tiny fixture built at test time inside tmp_path and labelled SYNTHETIC in its
provenance.json (explicit dev-only data; no real dataset is downloaded or
modified). The tests assert the honesty contract of `evaluate()`:

- no supervised metrics (no ground-truth labels exist),
- artifact promotion is REFUSED when training-data provenance is unknown,
- saved artifacts always carry an explicit REAL/SYNTHETIC data label.
"""

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import IsolationForest

from ml.features.schema_v1 import MLFeaturesV1, ML_FEATURE_SCHEMA_VERSION
from ml.training.evaluate import (
    evaluate,
    extract_provenance,
    format_report_markdown,
)
from ml.training.model_io import load_model

ARTIFACT_SOURCES = [
    "http://index.example/wat/000.warc.wat.gz",
    "http://index.example/wat/001.warc.wat.gz",
]


def build_fixture_frame(n_rows: int, seed: int = 7, origins: list[str] | None = None) -> pd.DataFrame:
    """A tiny MLFeaturesV1-conforming frame + metadata columns."""
    rng = np.random.default_rng(seed)
    features = MLFeaturesV1.feature_names()
    rows = []
    for i in range(n_rows):
        n_cookies = int(rng.integers(0, 4))
        kwargs = {
            "status_code": 200,
            "is_html": int(rng.integers(0, 2)),
            "https_enabled": int(rng.integers(0, 2)),
            "hsts_present": int(rng.integers(0, 2)),
            "csp_present": int(rng.integers(0, 2)),
            "x_content_type_options_present": int(rng.integers(0, 2)),
            "x_frame_options_present": int(rng.integers(0, 2)),
            "referrer_policy_present": int(rng.integers(0, 2)),
            "permissions_policy_present": int(rng.integers(0, 2)),
            "cookie_count": n_cookies,
            "cookie_secure_ratio": float(rng.choice([0.0, 0.5, 1.0])),
            "cookie_httponly_ratio": float(rng.choice([0.0, 0.5, 1.0])),
            "cookie_samesite_strict_ratio": float(rng.choice([0.0, 0.5, 1.0])),
            "cookie_samesite_lax_ratio": float(rng.choice([0.0, 0.5, 1.0])),
            "cookie_samesite_none_ratio": float(rng.choice([0.0, 0.5, 1.0])),
            "server_header_present": int(rng.integers(0, 2)),
            "x_powered_by_present": int(rng.integers(0, 2)),
        }
        rows.append(kwargs)
    df = pd.DataFrame(rows)
    for col in ("status_code", "is_html", "https_enabled", "cookie_count"):
        df[col] = df[col].astype("int64")
    df["origin"] = origins or [f"fixture{i}.example" for i in range(n_rows)]
    df["server_header_value"] = [
        "nginx/1.24.0" if bool(v) else "" for v in df["server_header_present"]
    ]
    df["x_powered_by_value"] = [
        "PHP/8.1.0" if bool(v) else "" for v in df["x_powered_by_present"]
    ]
    return df


def write_dataset(
    data_dir: Path,
    n_train: int = 40,
    n_val: int = 10,
    n_test: int = 12,
    provenance: dict | None = None,
    seed: int = 7,
) -> Path:
    """Write a tiny parquet dataset + provenance.json into data_dir."""
    data_dir.mkdir(parents=True, exist_ok=True)
    origins = [f"site{i}.example" for i in range(n_train + n_val + n_test)]
    frames = {
        "train": build_fixture_frame(n_train, seed, origins[:n_train]),
        "val": build_fixture_frame(n_val, seed + 1, origins[n_train:n_train + n_val]),
        "test": build_fixture_frame(n_test, seed + 2, origins[n_train + n_val:]),
    }
    frames["full"] = pd.concat(frames.values(), ignore_index=True)
    for name, df in frames.items():
        df.to_parquet(data_dir / f"{name}.parquet", index=False)
    if provenance is None:
        provenance = {
            "data_label": "SYNTHETIC",   # explicit dev-fixture label (opt-in test data)
            "source_type": "synthetic",
            "crawl_id": "TEST-CRAWL",
            "segment": "fixture.warc.wat.gz",
            "wat_url": "",
        }
    (data_dir / "provenance.json").write_text(
        json.dumps(provenance), encoding="utf-8"
    )
    return data_dir


@pytest.fixture
def synthetic_dataset(tmp_path: Path) -> Path:
    return write_dataset(tmp_path / "processed")


@pytest.fixture
def artifact_dir(tmp_path: Path) -> Path:
    return tmp_path / "artifacts" / "isoforest_v1"


class TestEvaluateHonestyContract:
    def test_no_supervised_metrics_and_no_ground_truth_claim(
        self, synthetic_dataset: Path, artifact_dir: Path
    ):
        report = evaluate(
            synthetic_dataset,
            n_estimators=10,
            save_artifact=False,
            artifact_dir=artifact_dir,
        )
        assert report["no_ground_truth_labels"] is True
        for forbidden in (
            "accuracy", "precision", "recall", "f1", "roc_auc",
            "probability_of_compromise",
        ):
            assert forbidden in report["metrics_not_reported"]
        # No supervised score anywhere in the serialized report
        serialized = json.dumps(report, indent=2, default=str).lower()
        for forbidden in ('"accuracy":', '"precision":', '"recall":', '"f1":', '"roc_auc":'):
            assert forbidden not in serialized

    def test_provenance_flows_into_report(
        self, synthetic_dataset: Path, artifact_dir: Path
    ):
        report = evaluate(
            synthetic_dataset, n_estimators=10, save_artifact=False,
            artifact_dir=artifact_dir,
        )
        prov = report["provenance"]
        assert prov["data_label"] == "SYNTHETIC"
        assert prov["data_source"] == "synthetic"
        assert report["feature_schema_version"] == ML_FEATURE_SCHEMA_VERSION

    def test_markdown_carries_disclaimer_and_label(
        self, synthetic_dataset: Path, artifact_dir: Path
    ):
        report = evaluate(
            synthetic_dataset, n_estimators=10, save_artifact=False,
            artifact_dir=artifact_dir,
        )
        md = format_report_markdown(report)
        assert "NOT a probability" in md
        assert "SYNTHETIC" in md
        # No supervised metrics appear as report sections
        for section in ("Accuracy", "Precision", "Recall", "ROC-AUC"):
            assert section not in md


class TestEvaluateArtifact:
    def test_artifact_saved_and_labeled(
        self, synthetic_dataset: Path, artifact_dir: Path
    ):
        report = evaluate(
            synthetic_dataset, n_estimators=10, save_artifact=True,
            artifact_dir=artifact_dir,
        )
        assert report["artifact_dir"] == str(artifact_dir)
        assert report["artifact_skip_reason"] is None
        model, threshold, metadata = load_model(artifact_dir)
        assert isinstance(model, IsolationForest)
        assert math.isfinite(threshold)
        assert metadata.data_label == "SYNTHETIC"
        assert metadata.train_rows == 40

    def test_unknown_provenance_refuses_artifact(
        self, tmp_path: Path, artifact_dir: Path
    ):
        # provenance.json exists but carries NO data_label -> UNKNOWN.
        data_dir = write_dataset(
            tmp_path / "mystery",
            provenance={"source_type": "mystery_source", "crawl_id": "?"},
        )
        report = evaluate(
            data_dir, n_estimators=10, save_artifact=True,
            artifact_dir=artifact_dir,
        )
        assert report["provenance"]["data_label"] is None
        # Refusal guard: nothing was promoted.
        assert report["artifact_dir"] is None
        assert report["artifact_skip_reason"]
        assert not artifact_dir.exists() or not list(artifact_dir.iterdir())

    def test_scores_are_ranking_values_not_probabilities(
        self, synthetic_dataset: Path, artifact_dir: Path
    ):
        report = evaluate(
            synthetic_dataset, n_estimators=10, save_artifact=False,
            artifact_dir=artifact_dir,
        )
        lo, hi = report["scores_test"]["score_range"]
        # An Isolation-Forest score is bounded only as a ranking value; it is
        # NOT asserted to be within [0, 1] — that would falsely suggest a
        # probability.
        assert math.isfinite(lo) and math.isfinite(hi)
        rate = report["scores_test"]["anomaly_rate_at_threshold"]
        assert 0.0 <= rate <= 1.0


class TestFailurePaths:
    def test_missing_dataset_exits(self, tmp_path: Path):
        with pytest.raises(SystemExit):
            evaluate(tmp_path / "nothing", save_artifact=False,
                     artifact_dir=tmp_path / "a")


class TestExtractProvenance:
    def test_synthetic_label_from_source_type(self, tmp_path: Path):
        d = tmp_path / "proc"
        d.mkdir()
        (d / "provenance.json").write_text(
            json.dumps({"source_type": "synthetic"}), encoding="utf-8"
        )
        prov = extract_provenance(d)
        assert prov["data_label"] == "SYNTHETIC"

    def test_no_label_in_provenance_stays_unknown(self, tmp_path: Path):
        d = tmp_path / "proc"
        d.mkdir()
        (d / "provenance.json").write_text(
            json.dumps({"source_type": "unlabeled_source"}), encoding="utf-8"
        )
        # A local file with no label must NOT silently borrow the repo's
        # legacy pilot-report label.
        prov = extract_provenance(d)
        assert prov["data_label"] is None

    def test_missing_provenance_falls_back_to_repo_pilot_report(self, tmp_path: Path):
        prov = extract_provenance(tmp_path / "no-prov-here")
        # Legacy fallback reads the repo-root pilot report (the real-data run);
        # its data_label is REAL and must flow through unchanged.
        assert prov["data_label"] == "REAL"
        assert prov["crawl_id"].startswith("CC-MAIN-")
