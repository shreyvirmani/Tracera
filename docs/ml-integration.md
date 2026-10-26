# Tracera ML — Backend Integration Contract (`ml_analysis_v1`)

For the full-stack developer integrating ML output into the scan UI/API.

## TL;DR for UI work

- `GET /api/v1/scans/{id}` and `GET /api/v1/scans/{id}/report` gained an
  **optional additive field** `"ml_analysis"`. It is `null` for scans without
  stored features, otherwise an object with `"status"` of `"analyzed"` or
  `"unavailable"` (see `backend/app/ml/contract.py` for the field-by-field
  contract and canonical interpretation strings).
- Treat every `anomaly_score` as **display-only ranking context**. It is NOT a
  probability, NOT a risk weight, and MUST NOT (a) re-order risk tiers,
  (b) change deterministic findings, or (c) be averaged into the risk score.
- When `status == "unavailable"`, render nothing ML-specific (or a muted
  "ML unavailable" chip). Never synthesize a score.
- When `status == "analyzed"`, the UI must render the canonical
  `score_interpretation`/`interpretation` strings verbatim. `data_label`
  ("REAL"/"SYNTHETIC") must be visible next to any score: synthetic-trained
  scores carry no real-world meaning.
- `anomaly_flag` means "above the model's own P5 calibration threshold" — it
  is statistical rareness, not a rule hit.

## Field semantics (analyzed)

| Field | Meaning / handling |
|---|---|
| `status` | `"analyzed"` |
| `analysis_version` | `"ml_analysis_v1"` — version the UI against it |
| `feature_schema_version` | `"v1"` |
| `data_label` | `"REAL"` or `"SYNTHETIC"` — training-data provenance |
| `model_version` | artifact identifier, e.g. `isoforest_v1` |
| `anomaly_score` | float; higher = header/cookie config more atypical vs training corpus. Range unlimited; finite. |
| `anomaly_flag` | bool; score ≥ the saved threshold |
| `score_interpretation` | canonical explanation string |
| `interpretation` | longer canonical string incl. provenance |
| `detail` | `{"threshold", "train_rows", "scores_are_not_probabilities": true}` |

## Field semantics (unavailable)

`unavailability_reason` ∈ {`ml_disabled`, `ml_package_unavailable`,
`artifact_not_found`, `artifact_incompatible`, `artifact_corrupt`,
`invalid_features`, `analysis_error`} — actionable codes, shown or logged, but
the scan payload is otherwise identical.

## Guarantees provided by `backend/app/ml/service.py`

1. `analyze_scan_features()` **never raises** (total graceful degradation).
2. Wiring in `backend/app/api/v1/scans.py` is additionally wrapped in
   try/except, so even a contract bug cannot fail the scan response.
3. No fabrication: unavailable ML yields no score, and results are JSON-safe
   via `result_to_dict()`.

## Deployment checklist

1. **Matching stack.** sklearn/numpy versions in `backend/requirements.txt`
   MUST match `ml/requirements.txt` (the committed artifact at
   `ml/artifacts/isoforest_v1/` was trained with sklearn 1.9.1 / numpy 2.5.3).
2. **Artifact present.** Default location `ml/artifacts/isoforest_v1/`
   relative to repo root, or override with `ML_ARTIFACT_DIR`.
   Missing artifact ⇒ scans still work, `ml_analysis.unavailability_reason =
   "artifact_not_found"`.
3. **Config flags** (`backend/app/core/config.py`):
   - `ML_ANALYSIS_ENABLED` (default `true`)
   - `ML_ARTIFACT_DIR` (default `""` → repo-root artifacts)
4. **Retraining** changes the artifact in place; `model_version` +
   `trained_at` in metadata let the UI show which model produced a score.
5. **Copy rules.** Any user-facing ML text must include the disclaimer that
   the anomaly score is not a probability of compromise (strings are provided
   in the response; do not paraphrase into stronger/intimidating language).

## How to add the same wiring elsewhere (backend)

```python
from app.ml import analyze_scan_features, result_to_dict

result = analyze_scan_features(scan.features)      # never raises
payload = result_to_dict(result)                    # JSON-safe dict
```

Scan feature dicts map through `ml_features_from_scan_dict` (derives
`is_html` from `content_type`, mirrors the WAT/live adapter semantics) and are
validated against the same `MLFeaturesV1` contract used at training time.

## Reference results (current committed artifact)

From `ml/data/pilot/reports/evaluation_report.md` (REAL data,
CC-MAIN-2026-34): test-split agreement with the rules engine is 132/134;
Spearman vs the transparent baseline ≈ 0.81. Remember when scoping UI:
this is auxiliary context, not a headline feature.
