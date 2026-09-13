# Tracera ML Phase 6: Common Crawl WAT Pilot Report

**Generated:** 2026-09-12T23:44:07.220952
**Schema Version:** v1
**Real Common Crawl Data:** NO (synthetic fallback)
**Crawl ID:** CC-MAIN-2026-34
**Seed:** 42

## Dataset Summary
- **Total WAT records processed:** 5,000
- **Usable records (200 OK + HTML):** 985
- **Unique origins after dedupe:** 635
- **Duplicate rate:** 0.00%
- **Filtered (non-200):** 1,459
- **Filtered (non-HTML):** 2,556
- **Extraction failed:** 0

## Split Summary (70/15/15 by eTLD+1)
- **Train:** 436 rows, 154 groups (69.7%)
- **Val:**   94 rows, 33 groups (14.9%)
- **Test:**  105 rows, 34 groups (15.4%)
- **Leakage-free:** [OK]

## HTTP
- **HTTPS:** 70.7%
- **HTML:** 100.0%
- **Status codes:** {200: 635}

## Security Headers
- **hsts_present:** 241 present (38.0%), 394 absent
- **csp_present:** 176 present (27.7%), 459 absent
- **x_content_type_options_present:** 334 present (52.6%), 301 absent
- **x_frame_options_present:** 367 present (57.8%), 268 absent
- **referrer_policy_present:** 240 present (37.8%), 395 absent
- **permissions_policy_present:** 112 present (17.6%), 523 absent

## Cookies
- **Origins with cookies:** 434
- **Cookie count distribution:** {0: 201, 1: 137, 2: 98, 3: 79, 4: 52, 5: 36, 6: 32}
- **cookie_secure_ratio:** mean=0.450, median=0.500, range=[0.000, 1.000]
- **cookie_httponly_ratio:** mean=0.316, median=0.250, range=[0.000, 1.000]
- **cookie_samesite_strict_ratio:** mean=0.148, median=0.000, range=[0.000, 1.000]
- **cookie_samesite_lax_ratio:** mean=0.135, median=0.000, range=[0.000, 1.000]
- **cookie_samesite_none_ratio:** mean=0.088, median=0.000, range=[0.000, 1.000]

## Technology Disclosure
- **server_header_present:** 515 (81.1%)
- **x_powered_by_present:** 181 (28.5%)

## Domain Concentration
- **Unique eTLD+1 domains:** 221
- **Top 20 domains cover:** 57.6% of dataset
- **Cloud platform concentration:**
  - github.io: 27
  - herokuapp.com: 22
  - azurewebsites.net: 32
  - blogspot.com: 26
  - netlify.app: 33
  - vercel.app: 32
  - pages.dev: 25
  - firebaseapp.com: 27
  - amazonaws.com: 11
  - googleusercontent.com: 12

## Missingness
- **server_header_value:** 120 (18.9%)
- **x_powered_by_value:** 454 (71.5%)

## Sanity Checks
- **no_duplicate_origins:** [OK] PASS
- **no_eTLD1_leakage:** [OK] PASS
- **binary_features_are_binary:** [FAIL] FAIL
- **ratios_in_range:** [OK] PASS
- **cookie_count_non_negative:** [OK] PASS
- **status_codes_valid:** [OK] PASS

## Feature Quality Checks
- **status_code:** OK
- **is_html:** OK
- **https_enabled:** OK
- **hsts_present:** OK
- **csp_present:** OK
- **x_content_type_options_present:** OK
- **x_frame_options_present:** OK
- **referrer_policy_present:** OK
- **permissions_policy_present:** OK
- **cookie_count:** OK
- **cookie_secure_ratio:** non-binary values: [np.float64(0.6), np.float64(0.8), np.float64(0.6666666666666666), np.float64(0.5), np.float64(0.75), np.float64(0.3333333333333333), np.float64(0.8333333333333334), np.float64(0.4)]
- **cookie_httponly_ratio:** non-binary values: [np.float64(0.4), np.float64(0.5), np.float64(0.6666666666666666), np.float64(0.3333333333333333), np.float64(0.25), np.float64(0.6), np.float64(0.2), np.float64(0.16666666666666666), np.float64(0.75)]
- **cookie_samesite_strict_ratio:** non-binary values: [np.float64(0.4), np.float64(0.25), np.float64(0.2), np.float64(0.3333333333333333), np.float64(0.5), np.float64(0.16666666666666666)]
- **cookie_samesite_lax_ratio:** non-binary values: [np.float64(0.2), np.float64(0.4), np.float64(0.16666666666666666), np.float64(0.3333333333333333), np.float64(0.5), np.float64(0.25)]
- **cookie_samesite_none_ratio:** non-binary values: [np.float64(0.25), np.float64(0.5), np.float64(0.16666666666666666), np.float64(0.2), np.float64(0.3333333333333333)]
- **server_header_present:** OK
- **x_powered_by_present:** OK
