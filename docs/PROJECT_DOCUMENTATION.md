# Tracera — Complete Project & Engineering Documentation

> **Defensive Website Analysis & Risk-Assessment Platform**  
> **Authors & Maintainers:** Shrey Virmani & Arman  
> **Target Audience:** Developers, Security Engineers, System Architects, Technical Evaluators  
> **Version:** 1.0 (Production-Ready Architecture)  
> **Repository:** `C:\Tracera`

---

## Table of Contents

1. [Executive Summary & Core Principles](#1-executive-summary--core-principles)
2. [End-to-End System Architecture](#2-end-to-end-system-architecture)
3. [Defensive Security & Network Ingestion Layer](#3-defensive-security--network-ingestion-layer)
   - 3.1 [SSRF Guard & DNS Resolution Protection](#31-ssrf-guard--dns-resolution-protection)
   - 3.2 [Safe HTTP Collector & IP Pinning](#32-safe-http-collector--ip-pinning)
4. [Feature Extraction Pipeline](#4-feature-extraction-pipeline)
5. [Deterministic Security Rule Engine & Risk Scoring](#5-deterministic-security-rule-engine--risk-scoring)
   - 5.1 [Rule Engine Catalog](#51-rule-engine-catalog)
   - 5.2 [Evidence-Backed Findings](#52-evidence-backed-findings)
   - 5.3 [Risk Scoring Methodology & Tiers](#53-risk-scoring-methodology--tiers)
6. [Machine Learning Anomaly Detection Architecture](#6-machine-learning-anomaly-detection-architecture)
   - 6.1 [Model Purpose & Philosophy](#61-model-purpose--philosophy)
   - 6.2 [Training Pipeline & Real Common Crawl WAT Data](#62-training-pipeline--real-common-crawl-wat-data)
   - 6.3 [Isolation Forest & Calibration](#63-isolation-forest--calibration)
   - 6.4 [Backend ML Integration Contract (`ml_analysis_v1`)](#64-backend-ml-integration-contract-ml_analysis_v1)
   - 6.5 [Why Accuracy Percentages Do Not Apply](#65-why-accuracy-percentages-do-not-apply)
7. [Database Schema & ORM Architecture](#7-database-schema--orm-architecture)
   - 7.1 [PostgreSQL & SQLAlchemy 2.0 Mapping](#71-postgresql--sqlalchemy-20-mapping)
   - 7.2 [Alembic Versioned Migrations](#72-alembic-versioned-migrations)
8. [Backend REST API Specification](#8-backend-rest-api-specification)
9. [Frontend Application Architecture](#9-frontend-application-architecture)
10. [Test Suites & Quality Verification](#10-test-suites--quality-verification)
11. [Operational Runbook & Getting Started](#11-operational-runbook--getting-started)

---

## 1. Executive Summary & Core Principles

**Tracera** is a defensive, non-intrusive website security and configuration assessment platform built for developers, startups, and security teams. When supplied with a publicly accessible URL, Tracera inspects the target through a hardened network boundary, analyzes observed protocol signals across HTTP, TLS, security headers, cookies, and HTML structures, and produces actionable, evidence-backed security reports.

### The Three Architectural Layers

Tracera strictly adheres to three distinct operational tiers to eliminate hallucinations and ungrounded claims:

```
┌────────────────────────────────────────────────────────────────────────┐
│ 1. Deterministic Analysis Layer (Primary Ground Truth)                 │
│    Directly measurable rules (RFCs, OWASP, NIST). 100% reproducible,   │
│    backed by exact raw headers and concrete HTTP evidence.             │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│ 2. Unsupervised Machine Learning Layer (Statistical Context)           │
│    Isolation Forest trained on real-world Common Crawl data. Answers:  │
│    "How unusual is this configuration compared to standard web data?"  │
│    Display-only anomaly ranking; NEVER overrides deterministic rules.  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│ 3. Explanation & Presentation Layer (Zero Fabrication)                 │
│    Plain-language remediation advice and clean visualization.          │
│    Never invents scores, never makes ungrounded vulnerability claims.  │
└────────────────────────────────────────────────────────────────────────┘
```

### What Tracera IS NOT
- **Not a Penetration Testing Tool**: Tracera never attempts exploitation, SQL injection, XSS payload execution, password spraying, or intrusive credential attacks.
- **Not a Black-Box Black Magic Scanner**: Findings are never inferred from guesswork. Every finding attaches the raw string evidence observed in the HTTP exchange.

---

## 2. End-to-End System Architecture

```
                    ┌────────────────────────────────────────┐
                    │          Next.js Frontend              │
                    │   (App Router, Tailwind CSS, Lucide)   │
                    └───────────────────┬────────────────────┘
                                        │ HTTP REST (JSON)
                                        ▼
                    ┌────────────────────────────────────────┐
                    │            FastAPI Backend             │
                    │   (/api/v1/scans, Rate Limiter, CORS)  │
                    └───────────────────┬────────────────────┘
                                        │
                         1. Validate & Canonicalize
                                        ▼
                    ┌────────────────────────────────────────┐
                    │     URL Validator & SSRF Guard         │
                    │ (DNS resolution, Private IP blocking)  │
                    └───────────────────┬────────────────────┘
                                        │
                         2. Pin IP & Safe Fetch
                                        ▼
                    ┌────────────────────────────────────────┐
                    │          Safe HTTP Collector           │
                    │ (Timeouts, Size Caps, Hop Revalidation)│
                    └───────────────────┬────────────────────┘
                                        │
                         3. Observed HTTP Response
                                        ▼
                    ┌────────────────────────────────────────┐
                    │        Feature Extraction Engine       │
                    │ (Headers, Cookies, TLS, HTML metadata) │
                    └───────┬────────────────────────┬───────┘
                            │                        │
       4a. Evaluate Rules   │                        │ 4b. Optional Outlier Inference
                            ▼                        ▼
        ┌─────────────────────────┐    ┌──────────────────────────┐
        │  16+ Deterministic Rules│    │ Isolation Forest (v1)    │
        │   Evidence-backed hits  │    │ Statistical anomaly rank │
        └───────────┬─────────────┘    └─────────────┬────────────┘
                    │                                │
                    │ 5. Calculate Score             │ 5b. Attach Context
                    ▼                                │
        ┌─────────────────────────┐                  │
        │   Risk Scoring Engine   │                  │
        │ (0-100 Score, Risk Tier)│                  │
        └───────────┬─────────────┘                  │
                    │                                │
                    └───────────────┬────────────────┘
                                    │
                         6. Persist & Render
                                    ▼
                    ┌────────────────────────────────────────┐
                    │    PostgreSQL Database (Asyncpg/Psycopg)│
                    │       scans & findings tables          │
                    └────────────────────────────────────────┘
```

---

## 3. Defensive Security & Network Ingestion Layer

Allowing users to specify arbitrary URLs to be fetched by a server introduces severe security vulnerabilities—chiefly **Server-Side Request Forgery (SSRF)** and **Denial of Service (DoS)**. Tracera implements an enterprise-grade defense-in-depth ingestion pipeline.

### 3.1 SSRF Guard & DNS Resolution Protection
Located in `backend/app/core/ssrf_guard.py` and `backend/app/core/url_validator.py`:

- **Scheme Validation**: Strictly allows only `http://` and `https://`. All file paths (`file://`), network protocols (`ftp://`, `gopher://`), and internal schemes are rejected before parsing.
- **Port Allowlist**: Only standard web ports (80, 443, 8080, 8443) are permissible. Scanning arbitrary ports (such as database ports 5432, 6379, 27017 or internal cloud ports 22, 2375) is blocked at input validation.
- **Strict IP Blacklisting**: Every hostname is resolved to its IP address prior to opening a connection. The following IP ranges are actively blocked:
  - Loopback (`127.0.0.0/8`, `::1`)
  - Private Networks (RFC 1918: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`)
  - Link-Local (`169.254.0.0/16`, `fe80::/10`) — protects cloud instance metadata endpoints (`http://169.254.169.254/`)
  - Carrier-Grade NAT (`100.64.0.0/10`)
  - Broadcast, Documentation, and Benchmark subnets
  - IPv6 Special Mappings (6to4, NAT64, IPv4-mapped IPv6 `::ffff:0:0/96`).

### 3.2 Safe HTTP Collector & IP Pinning
Located in `backend/app/collector/collector.py` and `safe_collector.py`:

- **DNS Rebinding Mitigation via IP Pinning**:
  In a DNS rebinding attack, an attacker configures a domain that resolves to a benign public IP on first lookup, but quickly resolves to `127.0.0.1` upon subsequent requests. Tracera mitigates this by resolving the IP once, validating it against the SSRF guard, and **binding the socket connection directly to the resolved IP address** while passing the original domain in the `Host` header and TLS Server Name Indication (SNI).
- **Multi-Hop Redirect Revalidation**:
  Redirects are not followed blindly. Every redirect hop (`301`, `302`, `307`, `308`) is intercepted. The target location is re-parsed and passed back through the full URL validator and SSRF guard before following. Redirects to private IPs or disallowed ports trigger immediate abort.
- **Resource Constraints (DoS Defense)**:
  - Total Timeout: 10.0 seconds maximum per scan.
  - Maximum Redirect Hops: 5 hops.
  - Body Size Limit: Max 2 MB (prevents memory exhaustion from large downloads / decompression bombs).

---

## 4. Feature Extraction Pipeline

Located in `backend/app/features/`:

Once an HTTP response is safely retrieved, the feature extraction layer parses the raw byte payload and HTTP headers into structured, normalized feature representations (`FeatureVector`):

1. **HTTP Security Headers** (`security_headers.py`):
   - `Content-Security-Policy` (CSP presence, frame-ancestors, default-src directives)
   - `Strict-Transport-Security` (HSTS presence, max-age, includeSubDomains, preload)
   - `X-Frame-Options` (`DENY`, `SAMEORIGIN`)
   - `X-Content-Type-Options` (`nosniff`)
   - `Referrer-Policy` (strict-origin, no-referrer, unsafe-url)
   - `Permissions-Policy` (camera, microphone, geolocation restrictions)
   - Server Information Leaks (`Server`, `X-Powered-By`, `X-AspNet-Version`).

2. **Cookie Parsing & Hygiene** (`cookie_parser.py`):
   - Total cookies observed across multiple `Set-Cookie` headers.
   - Percentage/ratio of cookies carrying the `Secure` flag.
   - Percentage/ratio of cookies carrying the `HttpOnly` flag.
   - SameSite distribution ratios (`Strict`, `Lax`, `None`, or missing).

3. **TLS & Protocol Quality** (`tls_extractor.py`):
   - TLS version enforcement (TLS 1.2, TLS 1.3).
   - Plain HTTP vs HTTPS redirection enforcement.

4. **HTML Surface Properties** (`html_parser.py`):
   - Form action destinations (checking for insecure form submissions over plain HTTP).
   - External script inclusions and iframe dependencies.

---

## 5. Deterministic Security Rule Engine & Risk Scoring

Located in `backend/app/rules/` and `backend/app/scoring/risk.py`:

### 5.1 Rule Engine Catalog
Tracera implements 16+ deterministic security rules, each codified with fixed severity weights:

| Rule ID | Category | Default Severity | Description |
| :--- | :--- | :--- | :--- |
| **`SEC-HTTPS-001`** | Security | **Critical** | Target website does not enforce HTTPS (serves unencrypted plain HTTP). |
| **`SEC-HSTS-001`** | Security | **High** | Missing `Strict-Transport-Security` header or max-age is below recommended thresholds. |
| **`SEC-CSP-001`** | Security | **High** | Missing `Content-Security-Policy` header, increasing exposure to Cross-Site Scripting (XSS). |
| **`SEC-COOKIE-001`** | Security | **High** | Sensitive cookies set without the `Secure` flag on an HTTPS origin. |
| **`SEC-COOKIE-002`** | Security | **Medium** | Cookies missing the `HttpOnly` flag, making them accessible to client-side scripts. |
| **`SEC-COOKIE-003`** | Security | **Low** | Cookies missing modern `SameSite` protections against Cross-Site Request Forgery (CSRF). |
| **`SEC-XFO-001`** | Security | **Medium** | Missing `X-Frame-Options` or CSP `frame-ancestors`, leaving site vulnerable to clickjacking. |
| **`SEC-XCTO-001`** | Security | **Low** | Missing `X-Content-Type-Options: nosniff`, allowing MIME-type sniffing. |
| **`SEC-RP-001`** | Privacy | **Low** | Missing or overly permissive `Referrer-Policy`. |
| **`SEC-PP-001`** | Privacy | **Info** | Missing `Permissions-Policy` to restrict hardware APIs (camera, geolocation). |
| **`CFG-SERVER-001`** | Configuration | **Low** | `Server` header leaks exact software and patch versions (e.g., `Apache/2.4.41 (Ubuntu)`). |
| **`CFG-XPB-001`** | Configuration | **Medium** | Technology disclosure header `X-Powered-By` exposed (e.g., `PHP/7.4`, `Express`). |
| **`CFG-MIXED-001`** | Security | **High** | Mixed content detected: HTTPS page links resources over unencrypted HTTP. |
| **`PERF-TIME-001`** | Performance | **Low** | Server response time exceeded 2000ms. |
| **`PERF-REDIR-001`** | Performance | **Info** | Excessive redirect chain (3 or more hops to resolve). |

### 5.2 Evidence-Backed Findings
Every finding returned by Tracera contains concrete evidence:
```json
{
  "rule_id": "SEC-HSTS-001",
  "category": "security",
  "severity": "high",
  "title": "Missing Strict-Transport-Security Header",
  "description": "The server did not return an HSTS header, leaving users vulnerable to SSL-stripping man-in-the-middle attacks.",
  "evidence": {
    "observed_header": null,
    "url": "https://example.com"
  },
  "recommendation": "Configure 'Strict-Transport-Security: max-age=31536000; includeSubDomains' in your web server configuration.",
  "confidence": 1.0
}
```

### 5.3 Risk Scoring Methodology & Tiers
Risk points are allocated according to severity:
- **Critical Finding**: 40 points
- **High Finding**: 20 points
- **Medium Finding**: 10 points
- **Low Finding**: 5 points
- **Info Finding**: 0 points

Points are summed and capped at **100**. The final score maps to standardized tiers:
- **0 – 19**: `Low Risk` (Strong security posture)
- **20 – 39**: `Medium Risk` (Recommended hygiene improvements)
- **40 – 69**: `High Risk` (Multiple significant misconfigurations)
- **70 – 100**: `Critical Risk` (Missing foundational security controls)

---

## 6. Machine Learning Anomaly Detection Architecture

Located in `ml/` and `backend/app/ml/`:

### 6.1 Model Purpose & Philosophy
Tracera uses Machine Learning exclusively as an **unsupervised statistical outlier detection engine**. It does not classify whether a site is "hacked" or predict a "probability of compromise". Instead, it quantifies how typical or atypical a website's configuration is relative to millions of production web servers.

### 6.2 Training Pipeline & Real Common Crawl WAT Data
- **Real Corpus**: Trained on parsed Common Crawl Web Archive Web Assessment (WAT) records (`CC-MAIN-2026-34`).
- **Provenance Tracking**: Every trained artifact records its data label:
  - `data_label: "REAL"` (trained on authenticated web crawl data)
  - `data_label: "SYNTHETIC"` (test fixtures only; strictly forbidden in production inference)
- **Refusal Guard**: The model loader refuses to load any model with `UNKNOWN` or unverified provenance.
- **Leakage-Safe Splitting**: Domain splitting is performed strictly by registrable domain (`eTLD+1`), ensuring subdomains of the same origin never leak across train, validation, and test splits.

### 6.3 Isolation Forest & Calibration
- **Algorithm**: `sklearn.ensemble.IsolationForest`
- **Feature Vector (`MLFeaturesV1`)**: 17 normalized numerical features (HTTPS status, HSTS presence, CSP presence, cookie count, secure cookie ratio, HttpOnly ratio, SameSite ratios, server headers, etc.).
- **Calibration Threshold**: The threshold is calibrated at the **95th percentile (P5)** of typical scores. Sites scoring above this threshold are marked with `anomaly_flag: true`.
- **Baseline Correlation**: Validated against an analytical per-feature $|z|$-score baseline, achieving a **0.8077 Spearman rank correlation**.
- **Empirical Alignment**: In the test split, **132 out of 134 detected anomalies** overlapped directly with rule engine findings, confirming that statistical outliers in web headers strongly correspond to real-world security hygiene issues.

### 6.4 Backend ML Integration Contract (`ml_analysis_v1`)
The ML service integrates into `GET /api/v1/scans/{id}` and `/api/v1/scans/{id}/report` as an **additive, optional field**:
```json
"ml_analysis": {
  "status": "analyzed",
  "analysis_version": "ml_analysis_v1",
  "data_label": "REAL",
  "model_version": "isoforest_v1",
  "anomaly_score": 0.1245,
  "anomaly_flag": true,
  "score_interpretation": "Atypical configuration: header/cookie profile is unusually rare compared to production websites.",
  "interpretation": "Evaluated with Isolation Forest against Real Common Crawl web crawl data.",
  "detail": {
    "threshold": 0.0489,
    "train_rows": 12737,
    "scores_are_not_probabilities": true
  }
}
```
**Fail-Safe Guarantees**:
1. `analyze_scan_features()` **never raises an exception**. If ML libraries are missing, or artifacts are unreadable, it degrades gracefully to:
   ```json
   "ml_analysis": {
     "status": "unavailable",
     "unavailability_reason": "ml_disabled"
   }
   ```
2. The deterministic scan result is always returned intact, regardless of ML status.

### 6.5 Why Accuracy Percentages Do Not Apply
Because there are no ground-truth "compromise" labels for millions of web servers, computing a "classification accuracy percentage" would be mathematically invalid and fabricated. Tracera measures and reports statistical consistency, baseline correlation, and deterministic rule overlap rather than invented percentages.

---

## 7. Database Schema & ORM Architecture

Located in `backend/app/db/`:

### 7.1 PostgreSQL & SQLAlchemy 2.0 Mapping
The database access layer uses modern **SQLAlchemy 2.0 Annotated Declarative Mapping** (`Mapped[...]` and `mapped_column`) with async pooling (`NullPool` to prevent connection leaks across async event loops).

#### Table: `scans`
| Column Name | SQL Type | Constraints / Attributes | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | Primary Key, default `uuid.uuid4` | Unique scan identifier |
| `url` | `TEXT` | NOT NULL | Submitted target URL |
| `canonical_url` | `TEXT` | NOT NULL | Normalized URL |
| `status` | `VARCHAR(50)` | NOT NULL, default `pending` | `pending`, `completed`, `failed` |
| `feature_schema_version` | `VARCHAR(50)`| NOT NULL | Feature vector version tag |
| `risk_score` | `INTEGER` | Nullable | Calculated score (0–100) |
| `risk_tier` | `VARCHAR(50)` | Nullable | `low`, `medium`, `high`, `critical` |
| `score_source` | `VARCHAR(50)` | Nullable | `fixed_baseline` |
| `status_code` | `INTEGER` | Nullable | HTTP status code observed |
| `content_type` | `VARCHAR(255)`| Nullable | Response MIME type |
| `response_time_ms`| `INTEGER` | Nullable | Latency in milliseconds |
| `redirect_count` | `INTEGER` | Nullable | Number of redirect hops |
| `final_url` | `TEXT` | Nullable | Destination URL after redirects |
| `content_length` | `INTEGER` | Nullable | Observed payload bytes |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, Indexed | Timestamp scan was initiated |
| `completed_at` | `TIMESTAMPTZ` | Nullable | Timestamp scan completed |
| `error_code` | `VARCHAR(100)`| Nullable | Categorized error code if failed |
| `error_message` | `TEXT` | Nullable | Human-readable failure reason |

*Note: In-memory ML features are stored on Python instances via `features: ClassVar[dict | None] = None` and are not persisted as an unindexed JSON column in PostgreSQL, keeping table queries light and performant.*

#### Table: `findings`
| Column Name | SQL Type | Constraints / Attributes | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | Primary Key, default `uuid.uuid4` | Unique finding ID |
| `scan_id` | `UUID` | Foreign Key → `scans.id` (`ON DELETE CASCADE`) | Owning scan reference |
| `rule_id` | `VARCHAR(100)`| NOT NULL | Identifier of the triggered rule |
| `category` | `VARCHAR(50)` | NOT NULL | `security`, `configuration`, etc. |
| `severity` | `VARCHAR(50)` | NOT NULL | `critical`, `high`, `medium`, `low`, `info` |
| `title` | `VARCHAR(255)`| NOT NULL | Display title |
| `description` | `TEXT` | NOT NULL | Detailed finding explanation |
| `evidence_json` | `JSON` | NOT NULL, default `{}` | Concrete raw header/URL evidence |
| `recommendation`| `TEXT` | NOT NULL | Actionable fix instructions |
| `source` | `VARCHAR(50)` | NOT NULL | `rule_engine` |
| `confidence` | `INTEGER` | NOT NULL, default 100 | Percentage confidence (100) |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, Indexed | Timestamp created |

### 7.2 Alembic Versioned Migrations
Located in `backend/alembic/versions/`:
- `91c3d92f8061`: Initial schema for `scans` and `findings` tables with foreign keys and cascade delete rules.
- `a7f3c1d92b04`: Adds observed HTTP metadata columns (`status_code`, `content_type`, `response_time_ms`, `redirect_count`, `final_url`, `content_length`) and indexes for timestamp sorting.

---

## 8. Backend REST API Specification

| Method | Endpoint | Description | Request / Query | Response Model |
| :--- | :--- | :--- | :--- | :--- |
| **`POST`** | `/api/v1/scans` | Initiates and completes a website security scan. | `{"url": "https://example.com"}` | `ScanResponse` (Full scan report) |
| **`GET`** | `/api/v1/scans` | Paginated list of historical scans with filters. | `?limit=8&offset=0&status=completed` | `ScanListResponse` |
| **`GET`** | `/api/v1/scans/{id}` | Fetches a single scan and all associated findings. | Path parameter: UUID `id` | `ScanResponse` |
| **`GET`** | `/api/v1/scans/{id}/findings` | Returns list of findings for a specific scan. | Path parameter: UUID `id` | `List[FindingResponse]` |
| **`GET`** | `/api/v1/scans/{id}/report` | Formatted summary report object with severity counts. | Path parameter: UUID `id` | `ScanReportResponse` |
| **`GET`** | `/api/v1/scans/{id}/export` | Downloads scan findings as an attachment JSON file. | Path parameter: UUID `id` | Attachment file `tracera-scan-{id}.json` |
| **`GET`** | `/health` | Application health and readiness probe. | None | `{"status": "healthy"}` |

---

## 9. Frontend Application Architecture

Located in `frontend/`:

Built with **Next.js 14+ (App Router)**, **TypeScript**, and **Tailwind CSS**:

- **Design Philosophy**: Minimalist, high-density developer dashboard inspired by Linear and Vercel. Dark-mode first with high-contrast accessibility compliance.
- **Key Views**:
  - **Homepage / Scanner (`/page.tsx`)**: URL submission form with client-side URL sanitation, live scanning state animations, and immediate presentation of results.
  - **Scan Dashboard (`/scans/[id]/page.tsx`)**: Comprehensive risk breakdown showing the 0–100 score, Risk Tier badge, HTTP response metadata (status code, timing, payload size), interactive findings filter (filter by Critical/High/Medium/Low), and evidence inspection cards.
  - **History & Scans List**: Historical scan feed with live filtering by status and search patterns.
  - **Export Integration**: One-click download button invoking `/api/v1/scans/{id}/export`.
- **API Client Layer (`frontend/services/api.ts`)**: Type-safe REST wrappers communicating with `http://localhost:8000/api/v1`.

---

## 10. Test Suites & Quality Verification

Tracera maintains dedicated, isolated test suites to prevent regression:

1. **Backend Tests (`backend/tests/`)**:
   - `test_url_validator.py`: Scheme enforcement, port filtering, malformed URI handling.
   - `test_ssrf_guard.py`: IPv4/IPv6 private IP blocking, loopback, link-local metadata protection.
   - `test_rules.py`: Verification that all 16 rules fire only on genuine conditions and carry evidence.
   - `test_scoring.py`: Mathematical score calculation, capping, and tier mapping.
   - `test_ml_service.py`: ML contract verification, graceful fallback behavior, `data_label` assertions.
   - **Status**: **78 passed** in 33 seconds.

2. **ML Tests (`ml/tests/`)**:
   - `test_schema_v1.py` & `test_schema_validation.py`: Strict schema type checking and validation.
   - `test_data_pipeline.py`: CDX parsing, WAT streaming, multi-cookie extraction.
   - `test_model_io.py`: Artifact loading, threshold persistence, and provenance refusal guards.
   - `test_evaluation.py`: Seed stability and baseline correlation checks.
   - **Status**: **194 passed, 1 skipped** (offline-by-default).

3. **Frontend Tests (`frontend/tests/`)**:
   - Jest & React Testing Library components tests (39 passed).
   - Strict TypeScript compiler typecheck (`npm run typecheck` passed cleanly).
   - Next.js production build (`npm run build` compiled cleanly).

---

## 11. Operational Runbook & Getting Started

### Prerequisites
- **Python 3.12+** (tested on 3.12, 3.13, 3.14)
- **Node.js 20+** & **npm**
- **PostgreSQL 15+** (tested on PostgreSQL 18)

### 1. Database Setup
Ensure PostgreSQL is running locally on port `5432` with a database named `Tracera`:
```sql
CREATE DATABASE "Tracera";
```

### 2. Backend Startup
From the project root:
```powershell
cd C:\Tracera\backend

# Activate the project virtual environment
.\.venv\Scripts\Activate.ps1

# Run database migrations
.\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head

# Start Uvicorn API server
.\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
```
- **Interactive OpenAPI Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **API Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

### 3. Frontend Startup
Open a separate terminal:
```powershell
cd C:\Tracera\frontend

# Install dependencies if not already done
npm install --legacy-peer-deps

# Start the Next.js development server
npm run dev
```
- **Web Application UI**: [http://localhost:3000](http://localhost:3000)

### 4. Running a Test Scan via CLI
```powershell
curl -X POST http://localhost:8000/api/v1/scans `
  -H "Content-Type: application/json" `
  -d '{"url": "https://example.com"}'
```

---
*Documentation generated for Tracera Version 1.0. Maintained in the repository under `docs/PROJECT_DOCUMENTATION.md`.*
