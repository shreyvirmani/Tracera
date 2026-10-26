# Tracera ML — Audit Report (Phase A)

Date: 2026-10-25
Audited branch: `feature/shrey-ml-setup` (commit `427021b`)
Auditor: ML component (Shrey)

## 1. What actually exists today

| Component | Status | Notes |
|---|---|---|
| `ml/features/schema_v1.py` | ✅ Working | `MLFeaturesV1` (17 features), `DatasetMetadata`, production adapter. No runtime validation of values (types, ranges, finiteness). Docstring header counts are wrong ("Security Headers (5)" — there are 6). |
| `ml/preprocessing/` | ✅ Working, ❌ duplicated code | `normalize.py` defines `get_public_suffix_list`, `_traverse_psl_tree`, `get_correct_public_suffix`, `_count_labels`, `_is_cloud_platform_domain`, `normalize_url`, `normalize_origin`, `extract_registrable_domain_from_url` **twice each**; later definitions silently shadow earlier ones. |
| `ml/data/pilot.py` | ❌ Broken against real data | 9 confirmed defects (§3). Also **shadowed by the package `ml/data/pilot/`** — `import ml.data.pilot` resolves to the package, so the script can only be run by direct file execution. |
| `ml/data/pilot/processed/*.parquet` | ⚠️ Synthetic, tracked in git | The committed pilot dataset (635 origins) is entirely **synthetic** (report says `Real Common Crawl Data: NO`). Git-tracked despite `.gitignore` listing the directory. |
| `ml/training/track_b_isoforest.py` | ⚠️ Limited value | Runs on synthetic data only; no model artifact saved; no baseline comparison; rule-overlap analysis is a hard-coded placeholder (`'note': 'No deterministic rule findings available'`). |
| `ml/data/http_archive/` | ⚠️ Incomplete | `run_http_archive_pilot` ends with `# The rest of the pipeline would continue here...` — it acquires (or falls back to synthetic) and returns without processing. SQL query references `httparchive.crawl.pages` while `config.py` defaults to `summary_pages`; `query.sql` file ≠ inline query. README contains duplicated tree entries. |
| Backend `app/ml/` | ❌ Empty | File exists, no content. No ML integration in the scan pipeline. |
| Root directory | ⚠️ Clutter | ~20 one-off debug scripts (`check_*.py`, `fix_*.py`, `new_query*.txt`) committed at repo root from BigQuery debugging. |
| `.gitignore` | ⚠️ Inconsistent | Ignores `*.json` globally (blocks future reports) yet dataset/results were force-committed anyway. |

## 2. Baseline test results (executed)

- `ml` suite: **126 passed** (18.1 s)
- `backend` suite: **58 passed** (1.8 s)

## 3. Confirmed real-data blockers (reproduced live, 2026-10-25)

Live probes against Common Crawl (`CC-MAIN-2026-34`) established that **the real data IS accessible** from this environment and the pipeline failures were code defects, not access problems:

1. **CDX index parse bug** — the index API returns `urlkey timestamp {json}`; `pilot.py` does `json.loads(line.split(' ', 1)[1])` which leaves the leading timestamp → `JSONDecodeError: Extra data` on **every** line → no WAT filename → synthetic fallback. Verified live: status 200, valid payload.
2. **WAT filename derivation wrong** — code builds `.../wat/CC-MAIN-...wat.gz`; the correct object name is `CC-MAIN-...warc.wat.gz`. Verified live: 404 on the wrong name, HTTP 206 with valid gzip WAT content on the correct name (segment = 149 MB, Range requests supported).
3. **Real WAT response records have no `Status` field** — synthetic records carried `Status: "200"`; real records carry `Response-Message: "HTTP/1.1 200 OK"`. The extractor reads `Status`, gets 0, and filters **every real record as non-200**. This is the primary "real WAT unusable" defect.
4. **Multi-record `Set-Cookie` handling** — real WAT headers store `Set-Cookie` as a **list** of cookie strings; the normalizer keeps only the first element (`v[0]`), under-counting cookies.
5. **`warc_filename` provenance is fake** — code stores `WARC-Payload-Digest` in the `warc_filename` field.
6. **Multi-member gzip not handled** — WAT files are concatenated gzip members; a naive single-member gzip read stops after the first record.
7. **Silent synthetic substitution** — on any failure the pipeline substitutes synthetic data with only a printed warning and labels results as if real. This violates the project constraint ("never silently substitute synthetic data").
8. **Module shadowing** — `ml/data/pilot.py` vs package `ml/data/pilot/`.
9. **No caching/restartability** — every run re-downloads and re-streams raw data.

## 4. Risks

- **R1 (highest):** Claims built on the synthetic dataset. All committed pilot results are synthetic; nothing measured on real websites.
- **R2:** Anomaly score semantics uncontrolled — no artifact exists, so there is no ML inference in the product at all; but once added, an IsoForest score must never be presented as "probability of compromise" (it is a typicality/geo-density measure trained on crawled-page statistics, not exploit evidence).
- **R3:** Training/inference skew risk — backend `FeatureVector` (35+ fields incl. TLS/HTML) vs ML `MLFeaturesV1` (17); conversion exists (adapter) but nothing at inference time validates the 17 values (ranges/types/finiteness).

## 5. Prioritized implementation plan

1. **P0 — Feature schema validation (Phase C):** add `validate()`/`from_dict`/round-trip tests; fix doc comments.
2. **P0 — Real data pipeline fix (Phase B):** fix all 9 defects; download-to-cache (restartable); strict source labeling; synthetic data becomes an explicit opt-in dev fixture, never a silent fallback; then **run the pilot on real Common Crawl data**.
3. **P1 — Evaluation framework (Phase D):** reproducible evaluation with (a) baseline, (b) IsoForest, (c) deterministic-rule overlap comparison; model artifact + metadata; explicit limitation labelling (no supervised metrics without labels).
4. **P1 — Backend integration (Phase E):** versioned, graceful `ml_analysis` contract in `backend/app/ml/`; optional additive scan-result field; never blocks the scan.
5. **P2 — Cleanup:** dedupe `normalize.py`; archive root debug scripts; artifact/cache git policy; `ml/README.md` with reproducible workflow.
