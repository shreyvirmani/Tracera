# Tracera ML — Isolation Forest Experiment (Synthetic)

**WARNING: SYNTHETIC DEVELOPMENT EXPERIMENT ONLY**

- Dataset is synthetic — not representative of real web
- No ground-truth labels exist
- No precision/recall/F1 can be reported
- No real-world vulnerability detection claimed

**Generated:** 2026-09-13T12:49:26.485322
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
- Anomalies detected: 47 (7.40%)
- Score range: [-0.0547, 0.1763]
- Score mean: 0.0722, std: 0.0488

## Top 25 Anomalies
1. https://staging472.netlify.app:443 (score: -0.0547, domain: netlify.app)
2. https://myapp2240.azurewebsites.net:443 (score: -0.0533, domain: azurewebsites.net)
3. https://myapp64.azurewebsites.net:443 (score: -0.0530, domain: azurewebsites.net)
4. https://staging.wixsite.com:443 (score: -0.0504, domain: wixsite.com)
5. https://staging325.vercel.app:443 (score: -0.0431, domain: vercel.app)
6. http://shopify.ac.uk:80 (score: -0.0378, domain: shopify.ac.uk)
7. https://myapp597.vercel.app:443 (score: -0.0376, domain: vercel.app)
8. https://media.wordpress.com.hk:443 (score: -0.0355, domain: wordpress.com.hk)
9. https://shopify.org.au:443 (score: -0.0349, domain: shopify.org.au)
10. https://myapp865.github.io:443 (score: -0.0343, domain: github.io)
11. https://app891.firebaseapp.com:443 (score: -0.0337, domain: firebaseapp.com)
12. https://news.weebly.com:443 (score: -0.0306, domain: weebly.com)
13. https://myapp177.netlify.app:443 (score: -0.0263, domain: netlify.app)
14. https://myapp624.pages.dev:443 (score: -0.0263, domain: pages.dev)
15. http://azurewebsites.net:80 (score: -0.0257, domain: azurewebsites.net)
16. https://wiki.squarespace.com:443 (score: -0.0222, domain: squarespace.com)
17. https://store.netlify.com:443 (score: -0.0218, domain: netlify.com)
18. https://dev.render.com:443 (score: -0.0213, domain: render.com)
19. http://beta.github.io:80 (score: -0.0212, domain: github.io)
20. https://staging874.vercel.app:443 (score: -0.0211, domain: vercel.app)
21. http://demo.firebaseapp.com:80 (score: -0.0210, domain: firebaseapp.com)
22. https://news.azurewebsites.net:443 (score: -0.0206, domain: azurewebsites.net)
23. https://googleusercontent.com.au:443 (score: -0.0205, domain: googleusercontent.com.au)
24. http://wixsite.com.au:80 (score: -0.0201, domain: wixsite.com.au)
25. https://static.pages.org.au:443 (score: -0.0188, domain: pages.org.au)

## Rule Overlap Analysis
- Total anomalies: 47
- Rule-overlap: 0
- Potentially novel: 0
- Weak/irrelevant: 47
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