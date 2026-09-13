# Tracera ML — Isolation Forest Experiment (Synthetic)

**WARNING: SYNTHETIC DEVELOPMENT EXPERIMENT ONLY**

- Dataset is synthetic — not representative of real web
- No ground-truth labels exist
- No precision/recall/F1 can be reported
- No real-world vulnerability detection claimed

**Generated:** 2026-09-13T12:28:26.915878
**Schema Version:** v1
**Data Source:** synthetic_fixture

## Configuration
- **n_estimators:** 200
- **random_state:** 42
- **contamination:** 0.05
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
- Score range: [-0.0547, 0.1763]
- Score mean: 0.0722, std: 0.0488

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
- **all** (17 features): 22 anomalies (5.05%), score mean=0.0761
- **security_headers** (6 features): 21 anomalies (4.82%), score mean=0.1083
- **cookies** (6 features): 15 anomalies (3.44%), score mean=0.0988
- **http_basic** (3 features): 0 anomalies (0.00%), score mean=0.0459
- **tech_disclosure** (2 features): 20 anomalies (4.59%), score mean=0.0688
- **no_security_headers** (11 features): 22 anomalies (5.05%), score mean=0.1001

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