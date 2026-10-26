# HTTP Archive BigQuery Data Pipeline

> ⚠️ **STATUS: EXPERIMENTAL / INCOMPLETE — superseded by `ml/data/cc_wat_pilot.py`.**
>
> The audit of this module (`docs/ml-audit.md`) found:
> - `extract.py` "synthetic fallback" mode is a **silent synthetic-for-real substitution**
>   and contradicts the data-honesty policy now in force (`ml/data/cc_wat_pilot.py`
>   requires an explicit `--source download|synthetic` and labels every artifact).
> - The orchestration stops mid-pipeline: the BigQuery result mapping is
>   incomplete ("The rest of the pipeline would continue here" — `extract.py`),
>   so this module has never produced a complete, validated real dataset.
>
> The working, validated acquisition route for real data is
> **`ml/data/cc_wat_pilot.py`** (Common Crawl WAT, real 2026 crawl, verified
> end-to-end). Use this module only as reference material for a future
> HTTP-Archive-specific extractor; do not trust its vocabulary maps or
> downstream behavior.

## Overview

This module extracts real-world web data from the HTTP Archive BigQuery dataset and transforms it into Tracera's 17-feature ML schema for anomaly detection research.

## Directory Structure

```
ml/data/http_archive/
├── __init__.py           # Package exports
├── config.py             # Configuration presets
├── query.sql             # BigQuery SQL template
├── extract.py            # Extraction & transformation pipeline
├── query.sql             # BigQuery SQL template (legacy)
├── config.py             # Configuration presets
├── extract.py            # Extraction & transformation pipeline
├── README.md             # This file
├── fixtures/             # Test fixtures
├── tests/                # Unit tests
│   ├── test_config.py
│   └── test_extract.py
└── reports/              # Generated reports
```

## Configuration

The pipeline uses `HTTPArchiveConfig` for all settings. Predefined presets are available in `config.py`:

- `2025_web_almanac_desktop` (default) - 2025 Web Almanac Desktop crawl
- `2025_web_almanac_mobile` - 2025 Web Almanac Mobile crawl
- `2024_web_almanac_desktop` - 2024 Web Almanac Desktop crawl
- `2024_web_almanac_mobile` - 2024 Web Almanac Mobile crawl

## Usage

### Dry Run (Preview Query)
```bash
python ml/data/http_archive/extract.py --config 2025_web_almanac_desktop --dry-run
```

### Run Full Pipeline
```bash
# With real BigQuery data (requires gcloud auth)
python ml/data/http_archive/extract.py --config 2025_web_almanac_desktop --max-origins 5000

# With synthetic fallback (for testing without BigQuery access)
python ml/data/http_archive/extract.py --config 2025_web_almanac_desktop --max-origins 5000

# Without synthetic fallback (fails if real data unavailable)
python ml/data/http_archive/extract.py --config 2025_web_almanac_desktop --max-origins 5000 --no-synthetic-fallback
```

### Configuration Options
```bash
python ml/data/http_archive/extract.py \
    --config 2025_web_almanac_desktop \
    --max-origins 10000 \
    --crawl-id 2025_07_01 \
    --client desktop \
    --output-dir ml/data/http_archive \
    --seed 42
```

## BigQuery Access

### Prerequisites
1. Google Cloud account with BigQuery API enabled
2. `gcloud auth application-default login` for authentication
3. Appropriate IAM permissions for `httparchive` dataset

### Data Source
- **Dataset**: `httparchive.summary_pages` (BigQuery public dataset)
- **Tables**: `YYYY_MM_DD_desktop` / `YYYY_MM_DD_mobile`
- **Region**: US (us-east-1)

### Access Methods
1. **BigQuery Python Client** (recommended): Uses `google-cloud-bigquery` with default credentials
2. **CloudFront/CDN**: Some files accessible via `https://data.commoncrawl.org/...`
3. **Direct S3**: Requires AWS credentials for `s3://commoncrawl/`

## Data Schema

The pipeline extracts exactly 17 model features matching `ml/features/schema_v1.py`:

### HTTP Features (3)
- `status_code` - HTTP response status
- `is_html` - Binary: 1 if Content-Type is text/html
- `https_enabled` - Binary: 1 if HTTPS scheme

### Security Headers (6)
- `hsts_present` - Strict-Transport-Security header present
- `csp_present` - Content-Security-Policy header present
- `x_content_type_options_present` - X-Content-Type-Options: nosniff
- `x_frame_options_present` - X-Frame-Options header present
- `referrer_policy_present` - Referrer-Policy header present
- `permissions_policy_present` - Permissions-Policy header present

### Cookies (6)
- `cookie_count` - Number of Set-Cookie headers
- `cookie_secure_ratio` - Fraction with Secure flag
- `cookie_httponly_ratio` - Fraction with HttpOnly flag
- `cookie_samesite_strict_ratio` - Fraction with SameSite=Strict
- `cookie_samesite_lax_ratio` - Fraction with SameSite=Lax
- `cookie_samesite_none_ratio` - Fraction with SameSite=None

### Tech Disclosure (2)
- `server_header_present` - Server header present
- `x_powered_by_present` - X-Powered-By header present

### Metadata (Separate from Model Features)
- `url`, `origin`, `registrable_domain`
- `crawl_timestamp`, `warc_filename`, `record_id`
- `server_header_value`, `x_powered_by_value`, `content_type`
- `cookie_info_available` (True if Set-Cookie header was present)

## Pipeline Steps

1. **Acquisition**: Stream data from BigQuery using parameterized query
2. **Filtering**: Keep only 200 OK HTML root pages
3. **Feature Extraction**: Map HTTP Archive fields to 17-feature schema
3. **Normalization**: Normalize origins, extract registrable domains (eTLD+1)
4. **Deduplication**: Keep latest record per origin
5. **Splitting**: 70/15/15 train/val/test split by registrable domain (eTLD+1)
6. **Output**: Parquet files + JSON/Markdown reports

## Output Files

```
ml/data/http_archive/
├── raw/                    # Raw BigQuery results (if saved)
├── processed/
│   ├── train.parquet       # Training split
│   ├── val.parquet         # Validation split
│   ├── test.parquet        # Test split
│   └── full.parquet        # Full deduplicated dataset
└── reports/
    ├── pilot_report.json   # Machine-readable report
    └── PILOT_REPORT.md     # Human-readable report
```

## BigQuery Access Requirements

### Authentication
```bash
# Set up Application Default Credentials
gcloud auth application-default login

# Or set GOOGLE_APPLICATION_CREDENTIALS env var
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

### Required Permissions
- `bigquery.jobs.create` on project
- `bigquery.tables.getData` on `httparchive.summary_pages.*`
- `bigquery.tables.get` on `httparchive.summary_pages.*`

### Cost Control
- Default max bytes billed: 10 GB per query
- Adjust with `--max-bytes-billed` or config `max_bytes_billed`

## Data Quality

### Cookie Semantics
The pipeline distinguishes:
- `cookie_count = 0` & `cookie_info_available = False` → No Set-Cookie header observed
- `cookie_count = 0` & `cookie_info_available = True` → Cookies exist but none have Secure/HttpOnly/SameSite flags
- `cookie_count > 0` → Ratios are meaningful

### Cloud Platform Grouping
For leakage-safe splitting, cloud platform domains are grouped:
- `github.io` → `github.io` (not `user.github.io`)
- `herokuapp.com` → `herokuapp.com`
- `azurewebsites.net` → `azurewebsites.net`
- `blogspot.com` (all TLDs) → `blogspot.com`
- `netlify.app`, `vercel.app`, `pages.dev`, etc.

## Testing

```bash
# Run all tests
pytest ml/data/http_archive/tests/ -v

# Run specific test file
pytest ml/data/http_archive/tests/test_config.py -v
pytest ml/data/http_archive/tests/test_extract.py -v
```

## Reports

The pipeline generates two reports:
- `pilot_report.json` - Machine-readable with all statistics
- `PILOT_REPORT.md` - Human-readable Markdown

Reports include:
- Dataset summary (counts, filtering stats)
- HTTP distribution (HTTPS %, HTML %)
- Security header presence rates
- Cookie statistics (counts, flag ratios)
- Technology disclosure (Server, X-Powered-By)
- Domain concentration (top domains, cloud platforms)
- Missingness analysis
- Feature quality checks
- Sanity checks (no leakage, duplicate detection)
- Split statistics (train/val/test sizes, group counts)

## License

Part of Tracera project. See root LICENSE.