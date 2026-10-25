#!/usr/bin/env python3
"""
Tracera ML — reproducible evaluation framework.

Evaluates on the pilot dataset (REAL Common Crawl WAT by default) whether the
**Isolation Forest** adds information beyond (a) a transparent statistical
baseline and (b) the deterministic rule engine.

What this framework reports (and deliberately does not):
- Reported: anomaly-score rankings & stability across seeds, agreement with a
  transparent per-feature z-score baseline, overlap with deterministic rule
  findings (categories A–D), record counts, provenance.
- NOT reported (impossible without ground-truth labels): accuracy, precision,
  recall, F1, ROC-AUC, or any "probability of compromise". An Isolation Forest
  measures statistical rareness; its score is NOT a security verdict.

Usage:
    python ml/training/evaluate.py --data-dir ml/data/pilot/processed
    python ml/training/evaluate.py --data-dir ... --feature-space synthetic   # dev only
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import IsolationForest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.features.schema_v1 import ML_FEATURE_SCHEMA_VERSION, MLFeaturesV1
from ml.features.dataframe import validate_feature_dataframe
from ml.features.rule_findings import compute_rule_findings_matrix
from ml.training.model_io import ModelMetadata, save_model

FEATURE_COLUMNS = MLFeaturesV1.feature_names()
SEEDS = [42, 123, 2026]


def load_dataset(data_dir: Path) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """Load processed parquet splits, validating every feature cell."""
    paths = {n: data_dir / f"{n}.parquet" for n in ("train", "val", "test", "full")}
    for name, p in paths.items():
        if not p.exists():
            raise SystemExit(
                f"[FAIL] missing {p}. Run the data pipeline first:\n"
                "       python ml/data/cc_wat_pilot.py --source download"
            )
    full = pd.read_parquet(paths["full"])
    feature_df, report = validate_feature_dataframe(full)
    if report.n_dropped or report.n_nan_coerced:
        print(f"[WARN] dataset validation: {report.to_dict()}")
    train = pd.read_parquet(paths["train"])
    val = pd.read_parquet(paths["val"])
    test = pd.read_parquet(paths["test"])
    return train, val, test, full, report.to_dict()


def train_isolation_forest(X: pd.DataFrame, seed: int, n_estimators: int = 200) -> Tuple[IsolationForest, float]:
    """Fit IsolationForest and derive the anomaly threshold from train scores."""
    model = IsolationForest(
        n_estimators=n_estimators,
        random_state=seed,
        contamination="auto",
        n_jobs=-1,
    )
    model.fit(X)
    train_scores = model.decision_function(X)
    threshold_normal_side = float(np.percentile(train_scores, 5))  # 5% of train below this
    return model, threshold_normal_side


def anomaly_scores(model: IsolationForest, X: pd.DataFrame) -> np.ndarray:
    """Higher = MORE anomalous (negative of decision_function)."""
    return -model.decision_function(X)


# ============================================================================
# Transparent baseline (no training, no randomness): mean per-feature |z|
# ============================================================================

def baseline_scores(train: pd.DataFrame, df: pd.DataFrame) -> np.ndarray:
    mu = train[FEATURE_COLUMNS].to_numpy(dtype=float).mean(axis=0)
    sd = train[FEATURE_COLUMNS].to_numpy(dtype=float).std(axis=0, ddof=0)
    sd_safe = np.where(sd < 1e-9, 1.0, sd)
    z = (df[FEATURE_COLUMNS].to_numpy(dtype=float) - mu) / sd_safe
    return z.mean(axis=1)


def top_k_jaccard(scores_a: np.ndarray, scores_b: np.ndarray, k: int) -> float:
    a = set(np.argsort(scores_a)[-k:].tolist())
    b = set(np.argsort(scores_b)[-k:].tolist())
    union = a | b
    return len(a & b) / len(union) if union else 0.0


# ============================================================================
# Evaluation
# ============================================================================

def evaluate(
    data_dir: Path,
    n_estimators: int = 200,
    seed: int = 42,
    save_artifact: bool = True,
    artifact_dir: Path = Path("ml/artifacts"),
) -> Dict[str, Any]:
    train, val, test, full, validation_report = load_dataset(data_dir)
    provenance = extract_provenance(data_dir)

    print("=" * 64)
    print("TRACERA ML EVALUATION")
    print("=" * 64)
    print(f"data_label: {provenance['data_label']}  source: {provenance['data_source']}")
    print(f"rows: train={len(train)} val={len(val)} test={len(test)}")

    # Sanity: prevent accidental non-real training data from being promoted
    if provenance["data_label"] != "REAL":
        print("[WARN] dataset label is NOT REAL — artifact will carry data_label="
              f"{provenance['data_label']} and must never be described as real-world-validated.")

    X_train = train[FEATURE_COLUMNS]
    X_val = val[FEATURE_COLUMNS]
    X_test = test[FEATURE_COLUMNS]

    # 1. Transparent baseline on the test split
    base_scores_test = baseline_scores(train, test)

    # 2. IsoForest (main seed)
    model, threshold = train_isolation_forest(X_train, seed, n_estimators)
    scores_test = anomaly_scores(model, X_test)

    # Baseline vs model agreement on test rankings (top-K)
    n_test = len(test)
    topk_agreement = {
        f"top_{k}": {
            "k": min(k, n_test),
            "jaccard": top_k_jaccard(scores_test, base_scores_test, min(k, n_test)),
        }
        for k in (10, 25, 50, 100)
        if min(k, n_test) >= 5
    }
    rho = spearmanr(scores_test, base_scores_test).statistic
    agreement_summary = {
        "baseline": "mean per-feature |z| (transparent, deterministic, no training)",
        "spearman_test": None if pd.isna(rho) else round(float(rho), 4),
        "topk_jaccard_test": topk_agreement,
        "interpretation": (
            "High overlap means the IsoForest mostly rediscovers the transparent "
            "baseline; low overlap means it adds a different ordering. Neither value "
            "alone justifies deployment."
        ),
    }

    # 3. Stability across seeds (top-K overlap on test)
    stability: Dict[str, Any] = {}
    seed_sets: Dict[int, np.ndarray] = {}
    for s in SEEDS:
        m, _ = train_isolation_forest(X_train, s, n_estimators)
        seed_sets[s] = anomaly_scores(m, X_test)
    for k in (25, 50):
        js = [
            top_k_jaccard(seed_sets[a], seed_sets[b], min(k, n_test))
            for i, a in enumerate(SEEDS) for b in SEEDS[i + 1:]
        ]
        stability[f"top_{k}"] = {
            "jaccard_mean": round(float(np.mean(js)), 4),
            "jaccard_min": round(float(np.min(js)), 4),
            "jaccard_max": round(float(np.max(js)), 4),
        }

    # 4. Overlap with deterministic rule findings (test split)
    rule_matrix = compute_rule_findings_matrix(test)
    rule_conflicts = find_feature_rule_mismatches(test, rule_matrix)
    n_rule_flagged = int((rule_matrix["n_rule_findings"] > 0).sum())
    anomaly_mask = scores_test >= -(threshold)  # anomaly_score >= -threshold
    a_and_r = int((rule_matrix["n_rule_findings"] > 0).to_numpy()[anomaly_mask].sum())
    anomaly_count = int(anomaly_mask.sum())
    rule_overlap = {
        "n_test": n_test,
        "n_rule_flagged_test": n_rule_flagged,
        "n_anomaly_test": anomaly_count,
        "feature_rule_mismatches": rule_conflicts,
        "categories": {
            "A_anomaly_with_rule_findings": a_and_r,
            "B_anomaly_without_rule_findings": anomaly_count - a_and_r,
            "C_rule_flagged_but_typical": int(n_rule_flagged - a_and_r),
            "D_neither": n_test - n_rule_flagged - anomaly_count + a_and_r,
        },
        "interpretation": (
            "A: model agrees with the rule engine. B: statistically unusual rows not "
            "covered by current rules — the only category where ML *may* add value; "
            "requires human review on real cases to confirm. C: rules fire but the "
            "configuration is common in the corpus — the rules remain the primary "
            "evidence-based signal. Counts, not metrics: no labels exist."
        ),
    }

    # 5. Persist artifact with explicit provenance
    artifact_path = None
    artifact_skip_reason = None
    if save_artifact:
        if provenance["data_label"] is None:
            # Refusal guard: an artifact whose training-data provenance is
            # unknown must never be promoted (it could later be mistaken for
            # real-world-validated). Produce/keep the evaluation report, but
            # save nothing.
            artifact_skip_reason = (
                "data_label is UNKNOWN (data_dir has a provenance.* record with "
                "no data_label) — refusing to save/promote a model artifact of "
                "unknown training-data provenance."
            )
            print(f"[FAIL] refusing to save artifact: {artifact_skip_reason}")
        else:
            artifact_dir.mkdir(parents=True, exist_ok=True)
            meta = ModelMetadata(
                model_version=f"isoforest_{ML_FEATURE_SCHEMA_VERSION}",
                model_class=type(model).__name__,
                feature_schema_version=ML_FEATURE_SCHEMA_VERSION,
                data_label=provenance["data_label"],
                data_source=provenance["data_source"],
                crawl_id=provenance["crawl_id"],
                train_rows=len(X_train),
                unique_origins=int(full["origin"].nunique()) if "origin" in full.columns else int(len(full)),
                params={"n_estimators": n_estimators, "random_state": seed},
                seeds=SEEDS,
                notes=[
                    "Score semantics: anomaly_score = -decision_function; HIGHER = MORE "
                    "statistically atypical. Not a probability of compromise/vulnerability.",
                    f"Threshold derived as P5 of training decision_function: {threshold:.6f}.",
                    "No ground-truth labels; no supervised metrics were computed.",
                ],
            )
            save_model(model, -threshold, meta, artifact_dir)
            artifact_path = str(artifact_dir)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "feature_schema_version": ML_FEATURE_SCHEMA_VERSION,
        "provenance": provenance,
        "validation": validation_report,
        "data_stats": {"train": len(X_train), "val": len(X_val), "test": len(X_test)},
        "model": {
            "class": type(model).__name__,
            "n_estimators": n_estimators,
            "seed": seed,
            "threshold_train_p5": round(float(-threshold), 6),
        },
        "scores_test": {
            "anomaly_rate_at_threshold": round(anomaly_count / max(n_test, 1), 4),
            "score_range": [float(scores_test.min()), float(scores_test.max())],
        },
        "baseline_agreement": agreement_summary,
        "seed_stability": stability,
        "rule_overlap": rule_overlap,
        "artifact_dir": artifact_path,
        "artifact_skip_reason": artifact_skip_reason,
        "metrics_not_reported": [
            "accuracy", "precision", "recall", "f1", "roc_auc",
            "probability_of_compromise", "maliciousness_classification",
        ],
        "no_ground_truth_labels": True,
    }
    return report


def extract_provenance(data_dir: Path) -> Dict[str, Any]:
    """
    Dataset provenance from `data_dir/provenance.json` (written by the pipeline).

    Rules (explicit, never invented):
    - If `provenance.json` exists it is authoritative: a missing `data_label`
      there stays UNKNOWN (None) — the caller must refuse artifact promotion.
    - Only when `provenance.json` is absent entirely (legacy datasets), fall
      back to the repo-root pilot report's `source` block; if that carries no
      label either, return data_label=None so callers refuse to promote.
    """
    provenance_path = Path(data_dir) / "provenance.json"
    if provenance_path.exists():
        raw = json.loads(provenance_path.read_text(encoding="utf-8"))
        label = raw.get("data_label") or (
            "SYNTHETIC" if raw.get("source_type") == "synthetic" else None
        )
    else:
        repo_root = Path(__file__).resolve().parents[2]
        report_path = repo_root / "ml" / "data" / "pilot" / "reports" / "pilot_report.json"
        raw = {}
        if report_path.exists():
            legacy = json.loads(report_path.read_text(encoding="utf-8"))
            source = legacy.get("source", legacy.get("pilot_info", {}))
            raw = dict(source) if source else {}
            raw.setdefault("data_label", legacy.get("data_label"))
        label = raw.get("data_label") or None
    return {
        "data_label": label,
        "data_source": str(raw.get("source_type", "")),
        "crawl_id": raw.get("crawl_id", ""),
        "segment": raw.get("segment", ""),
        "wat_url": raw.get("wat_url", ""),
    }


def find_feature_rule_mismatches(test: pd.DataFrame, rule_matrix: pd.DataFrame) -> Dict[str, int]:
    """Count semantic checks where the mirrored rules reproduce expected logic."""
    checks = {
        "SEC-COOKIE-002 fires only when cookies present": int(
            (rule_matrix["SEC-COOKIE-002"] & (test["cookie_count"] == 0)).sum()
        ),
        "SEC-HSTS-001 never fires on http": int(
            (rule_matrix["SEC-HSTS-001"] & (test["https_enabled"] == 0)).sum()
        ),
        "SEC-HTTPS-001 never fires on https": int(
            (rule_matrix["SEC-HTTPS-001"] & (test["https_enabled"] == 1)).sum()
        ),
        "CFG-XPB-001 requires x_powered_by_present": int(
            (rule_matrix["CFG-XPB-001"] & (test["x_powered_by_present"] == 0)).sum()
        ),
    }
    return checks


def format_report_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Tracera ML Evaluation Report",
        "",
        f"Generated: {report['generated_at']}",
        f"Data label: **{report['provenance']['data_label'] or 'UNKNOWN'}** "
        f"(source {report['provenance']['data_source'] or 'unknown'}, "
        f"crawl {report['provenance']['crawl_id'] or 'unknown'})",
        f"Feature schema: {report['feature_schema_version']}",
        "",
        "> ⚠️ An Isolation-Forest anomaly score measures statistical *rareness*.",
        "> It is NOT a probability of compromise, vulnerability, or maliciousness.",
        "> No ground-truth labels exist; no supervised metrics are reported.",
        "",
        "## Data",
    ]
    ds = report["data_stats"]
    lines.append(f"- train {ds['train']} / val {ds['val']} / test {ds['test']} (leakage-safe eTLD+1 split)")
    lines.append(f"- validation: {report['validation']}")
    lines.append(f"- anomaly rate at threshold: {report['scores_test']['anomaly_rate_at_threshold']:.2%}")
    lines += ["", "## Baseline comparison", f"- baseline: {report['baseline_agreement']['baseline']}"]
    lines.append(f"- Spearman (test scores): {report['baseline_agreement']['spearman_test']}")
    for k, v in report["baseline_agreement"]["topk_jaccard_test"].items():
        lines.append(f"- {k}: Jaccard {v['jaccard']:.3f}")
    lines.append("- " + report["baseline_agreement"]["interpretation"])
    lines += ["", "## Seed stability"]
    for k, v in report["seed_stability"].items():
        lines.append(f"- {k}: mean {v['jaccard_mean']}, min {v['jaccard_min']}, max {v['jaccard_max']}")
    lines += ["", "## Deterministic rule overlap (test split)"]
    cats = report["rule_overlap"]["categories"]
    lines.append(f"- A anomaly+rules: {cats['A_anomaly_with_rule_findings']}")
    lines.append(f"- B anomaly only: {cats['B_anomaly_without_rule_findings']}")
    lines.append(f"- C rules but typical: {cats['C_rule_flagged_but_typical']}")
    lines.append(f"- D neither: {cats['D_neither']}")
    for name, count in report["rule_overlap"]["feature_rule_mismatches"].items():
        lines.append(f"- mirror check {name}: {count} violations")
    lines.append("- " + report["rule_overlap"]["interpretation"])
    lines += ["", "## Artifact", f"- saved to: {report['artifact_dir']}"]
    lines += ["", "## Not reported", ", ".join(report["metrics_not_reported"])]
    return "\n".join(lines)


# ============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="Tracera ML evaluation")
    parser.add_argument("--data-dir", default="ml/data/pilot/processed")
    parser.add_argument("--n-estimators", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", default="ml/data/pilot/reports")
    parser.add_argument("--no-artifact", action="store_true")
    args = parser.parse_args()

    report = evaluate(
        data_dir=Path(args.data_dir),
        n_estimators=args.n_estimators,
        seed=args.seed,
        save_artifact=not args.no_artifact,
        artifact_dir=Path("ml/artifacts/isoforest_v1"),
    )
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "evaluation_report.json"
    md_path = out / "evaluation_report.md"
    json_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    md_path.write_text(format_report_markdown(report), encoding="utf-8")
    print(f"report: {json_path}")
    print(f"report: {md_path}")
    if report["provenance"]["data_label"] is None:
        # Unattended runs (CI / scheduled retrain) must not pass silently.
        print("[FAIL] evaluation ran on data with UNKNOWN provenance — exiting "
              "non-zero so this cannot be mistaken for a promotable run.")
        raise SystemExit(3)


if __name__ == "__main__":
    main()
