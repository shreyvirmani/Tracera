# Tracera ML Evaluation Report

Generated: 2026-10-25T17:14:26.634798+00:00
Data label: **REAL** (source common_crawl_wat, crawl CC-MAIN-2026-34)
Feature schema: v1

> ⚠️ An Isolation-Forest anomaly score measures statistical *rareness*.
> It is NOT a probability of compromise, vulnerability, or maliciousness.
> No ground-truth labels exist; no supervised metrics are reported.

## Data
- train 12737 / val 2662 / test 2690 (leakage-safe eTLD+1 split)
- validation: {'n_rows_in': 18089, 'n_rows_out': 18089, 'n_dropped': 0, 'n_nan_coerced': 0, 'n_type_coerced': 0, 'drop_reasons': {}}
- anomaly rate at threshold: 4.98%

## Baseline comparison
- baseline: mean per-feature |z| (transparent, deterministic, no training)
- Spearman (test scores): 0.8077
- top_10: Jaccard 0.176
- top_25: Jaccard 0.220
- top_50: Jaccard 0.389
- top_100: Jaccard 0.333
- High overlap means the IsoForest mostly rediscovers the transparent baseline; low overlap means it adds a different ordering. Neither value alone justifies deployment.

## Seed stability
- top_25: mean 0.7652, min 0.7241, max 0.7857
- top_50: mean 0.7284, min 0.6667, max 0.8519

## Deterministic rule overlap (test split)
- A anomaly+rules: 132
- B anomaly only: 2
- C rules but typical: 2534
- D neither: 22
- mirror check SEC-COOKIE-002 fires only when cookies present: 0 violations
- mirror check SEC-HSTS-001 never fires on http: 0 violations
- mirror check SEC-HTTPS-001 never fires on https: 0 violations
- mirror check CFG-XPB-001 requires x_powered_by_present: 0 violations
- A: model agrees with the rule engine. B: statistically unusual rows not covered by current rules — the only category where ML *may* add value; requires human review on real cases to confirm. C: rules fire but the configuration is common in the corpus — the rules remain the primary evidence-based signal. Counts, not metrics: no labels exist.

## Artifact
- saved to: ml\artifacts\isoforest_v1

## Not reported
accuracy, precision, recall, f1, roc_auc, probability_of_compromise, maliciousness_classification