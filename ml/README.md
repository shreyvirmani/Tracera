# Tracera ML

Defensible anomaly-detection research component for website risk assessment.

**What this is:** an Isolation Forest over 17 stable, low-cardinality HTTP
metadata features (`MLFeaturesV1`), trained on real Common Crawl data. It
produces an *anomaly score* (a statistical rareness ranking) and an optional
additive signal for the scan API.

**What this is NOT:** a vulnerability detector, a maliciousness verdict, or a
source of probabilities. There are **no ground-truth labels** anywhere in this
component, therefore no accuracy/precision/recall/F1/ROC-AUC is ever computed
or reported. Full reasoning: `docs/ml-audit.md`.

---

## Honest result (do not oversell when integrating)

`ml/data/pilot/reports/evaluation_report.md` — trained on REAL data
(CC-MAIN-2026-34 WAT segment, 18,089 unique origins):

- Test-split anomalies coincide with the deterministic rule engine in
  **132 of 134** cases (category A). Only **2** records are "anomaly-only"
  (category B — the only place where ML might add value; unverified without
  human review).
- Model scores correlate strongly with the transparent per-feature baseline
  (Spearman ≈ 0.81): the trained model ("Tier B") does not clearly outperform
  a simple transparent statistic ("Tier C").
- Conclusion: the rules engine remains the primary signal; the ML score is
  strictly additive context, and the product copy must reflect that.

## Labeling policy (enforced in code)

| Label       | Meaning                                                                  |
|-------------|--------------------------------------------------------------------------|
| `REAL`      | Trained on real crawler-collected data. Still not a verdict.             |
| `SYNTHETIC` | Dev/test fixture only — scores carry no real-world meaning.              |
| `None`      | Provenance unknown → **artifact promotion is refused** (`evaluate.py`).   |

- `data_label` travels through `model_metadata.json`, the eval report, and the
  API response (`ml_analysis.data_label`), so a synthetic-trained score can
  never be mistaken for real-world validated.
- Datasets carry a `provenance.json` next to the parquet splits (written by the
  pipeline). `evaluate.py` refuses to save an artifact if that label is unknown.

## Setup

```bash
python -m venv .venv
.venv\Scripts\pip install -r ml\requirements.txt   # Python 3.12 versions pinned
```

Backend (separate venv) needs the matching inference stack — see
`backend/requirements.txt` (sklearn/numpy MUST match the training env).

## Verifying real data access (do not assume)

```powershell
# Index API + Range-download probe handled by the pilot; run with network:
python ml\data\cc_wat_pilot.py --source download        # real crawl, ~10 min, 149 MB (then cached)
```

- Source of truth: `https://index.commoncrawl.org/CC-MAIN-2026-34-index` +
  `https://data.commoncrawl.org/.../wat/CC-MAIN-...warc.wat.gz`.
- The pipeline **never fabricates**: zero usable records → hard failure, and
  synthetic data is only produced with explicit `--source synthetic`,
  labeled SYNTHETIC everywhere.
- Cached downloads live in `ml/data/pilot/cache/` (git-ignored).

## Re-running the pilot (data)

```bash
python ml/data/cc_wat_pilot.py --source download        # REAL (network + 149 MB first run)
python ml/data/cc_wat_pilot.py --source synthetic       # dev-only fixture, explicit opt-in
```

Outputs: `ml/data/pilot/processed/{train,val,test,full}.parquet` +
`provenance.json` (tracked), `ml/data/pilot/reports/pilot_report.{json,md}`.
Data is NOT committed; regenerable via the command above.

## Re-running the evaluation (train + report)

```bash
python -m ml.training.evaluate --data-dir ml/data/pilot/processed
```

Retrains the artifact to `ml/artifacts/isoforest_v1/` (committed: deterministic
given seed), writes `ml/data/pilot/reports/evaluation_report.{json,md}`.
The report contains zero supervised metrics by construction
(`metrics_not_reported` list) and refuses promotion of unknown-provenance
artifacts (exit code 3).

## Test suite (offline by default)

```bash
python -m pytest ml -q
# Rotating live-network check (Common Crawl real access), opt-in only:
$env:TRACERA_NET_TESTS="1"; python -m pytest ml -q; Remove-Item Env:TRACERA_NET_TESTS
```

Baseline (2026-10-25, this branch): **194 passed, 1 skipped** (the network test).

## Module map

```
ml/
├── features/
│   ├── schema_v1.py         # MLFeaturesV1 + validate(); the 17-feature contract
│   ├── dataframe.py         # dataset-level validation/coercion w/ explicit report
│   └── rule_findings.py     # deterministic-rule mirror (backend/engine parity checks)
├── preprocessing/           # origin normalization, dedupe, leakage-safe split
├── data/
│   ├── cc_wat_pilot.py      # REAL Common Crawl WAT pipeline (validated path)
│   └── http_archive/        # EXPERIMENTAL/INCOMPLETE — see its README notice
├── training/
│   ├── evaluate.py          # evaluation framework + artifact promotion guard
│   ├── model_io.py          # artifact save/load + metadata validation
│   └── track_b_isoforest.py # legacy SYNTHETIC experiment (kept for the record)
├── artifacts/isoforest_v1/  # trained REAL artifact (committed)
└── data/pilot/              # pilot outputs: provenance.json tracked, parquets regenerable
```

## Known limitations

1. **No labels → no supervised claims.** Model agreement with rules (A/B/C/D
   counts) is the only comparability check; it is not accuracy.
2. **Corpus sampling bias.** Only sites crawled by Common Crawl during
   CC-MAIN-2026-34; features come from response *metadata* only (no body).
3. **Tier curve unproven.** The Isolation Forest did not beat the transparent
   baseline strongly enough to justify replacing rules with ML.
4. **Legacy code paths.** `track_b_isoforest.py` (SYNTHETIC experiment) and
   `ml/data/http_archive/` (incomplete) are kept for the record only.
5. **Single crawl segment.** One WAT segment; broadening coverage requires
   re-running the pilot over more segments (the pipeline restarts/caches).
