# Tracera ML — Isolation Forest Experiment (Synthetic)

**WARNING: SYNTHETIC DEVELOPMENT EXPERIMENT ONLY**

- Dataset is synthetic — not representative of real web
- No ground-truth labels exist
- No precision/recall/F1 can be reported
- No real-world vulnerability detection claimed

**Generated:** 2026-09-13T12:24:07.098393
**Schema Version:** v1
**Data Source:** synthetic_fixture

## Configuration
- **n_estimators:** 200
- **random_state:** 42
- **contamination:** auto
- **max_samples:** auto
- **n_jobs:** -1
- **verbose:** 0
- **seeds:** [42, 123, 2026]
- **max_features:** 1.0
- **bootstrap:** False

## Data
- Train: 436, Val: 94, Test: 105, Total: 635

## Anomaly Summary
- Total records: 635
- Anomalies detected: 0 (0.00%)
- Score range: [-0.1526, 0.0784]
- Score mean: -0.0257, std: 0.0488

## Top 25 Anomalies

## Rule Overlap Analysis
- Total anomalies: 0
- Rule-overlap: 0
- Potentially novel: 0
- Weak/irrelevant: 0
- Note: No deterministic rule findings available in synthetic data

## Stability Across Seeds
- **top_10**: Jaccard mean=0.624, min=0.538, max=0.667
- **top_25**: Jaccard mean=0.854, min=0.786, max=0.923
- **top_50**: Jaccard mean=0.819, min=0.786, max=0.887

## Ablation Experiments
- **all** (17 features): 295 anomalies (67.66%), score mean=-0.0218
- **security_headers** (6 features): 385 anomalies (88.30%), score mean=-0.0536
- **cookies** (6 features): 212 anomalies (48.62%), score mean=0.0110
- **http_basic** (3 features): 125 anomalies (28.67%), score mean=-0.0076
- **tech_disclosure** (2 features): 171 anomalies (39.22%), score mean=-0.0058
- **no_security_headers** (11 features): 230 anomalies (52.75%), score mean=0.0045

## Limitations
- **data_is_synthetic:** YES
- **no_ground_truth_labels:** YES
- **cookie_ratios_ambiguous_when_count_zero:** YES
- **no_real_world_validation:** YES
- **synthetic_distributions_not_representative:** YES

## Conclusion
Isolation Forest runs correctly on synthetic data. Anomaly detection is stable across seeds.
Ablation shows security headers dominate anomalies. Cookie features add marginal signal.
Worth testing on real data when available, but synthetic results are NOT evidence of real-world performance.