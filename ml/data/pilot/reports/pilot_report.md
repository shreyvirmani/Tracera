# Tracera ML Pilot Report — Common Crawl WAT

**Generated:** 2026-10-25T16:58:23.166451+00:00
**DATA LABEL:** REAL  ✅ real Common Crawl data
**Feature schema:** v1
**Crawl:** CC-MAIN-2026-34
**Segment:** CC-MAIN-20260807103001-20260807133001-00162.warc.wat.gz
**Seed:** 42

## Records
- **records_streamed:** 60,000
- **response_records:** 19,637
- **usable_records:** 19,637
- **filtered_non_200:** 0
- **filtered_non_html:** 363
- **filtered_other:** 40,000

## Validation
- rows in/out: 19,637 -> 19,637 (dropped 0)
- NaN coerced to defaults: 0
- type coercion columns: 0
- drop reasons: none

## Dedupe & split
- unique origins after dedupe: 18,089 (1,548 duplicate rows removed)
- train 12,737 / val 2,662 / test 2,690 — leakage-free: True

## HTTP
- HTTPS: 91.7%
- status codes: {'200': 18089}

## Security headers
- **hsts_present:** 5,612 present (31.0%)
- **csp_present:** 3,290 present (18.2%)
- **x_content_type_options_present:** 5,801 present (32.1%)
- **x_frame_options_present:** 4,562 present (25.2%)
- **referrer_policy_present:** 2,748 present (15.2%)
- **permissions_policy_present:** 1,484 present (8.2%)
- **x_powered_by_present:** 5,525 present (30.5%)

## Cookies
- origins with cookies: 8,374
- **cookie_secure_ratio:** mean=0.1859, median=0.0, range=[0.0, 1.0]
- **cookie_httponly_ratio:** mean=0.1818, median=0.0, range=[0.0, 1.0]
- **cookie_samesite_strict_ratio:** mean=0.0075, median=0.0, range=[0.0, 1.0]
- **cookie_samesite_lax_ratio:** mean=0.0668, median=0.0, range=[0.0, 1.0]
- **cookie_samesite_none_ratio:** mean=0.0714, median=0.0, range=[0.0, 1.0]

## Technology disclosure
- **server_header_present:** 16,638 (92.0%)
- **x_powered_by_present:** 5,525 (30.5%)

## Domains
- unique registrable domains: 17,501
- top 20 cover 1.7% of origins

## Limitations
- Feature extraction reads HTTP response metadata only (no page body content).
- Isolation of rare/odd patterns is NOT evidence of compromise or vulnerability.
- Dataset covers only sites crawled by Common Crawl during this crawl; sampling bias applies.