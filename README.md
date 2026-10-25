# Tracera

Website Risk Assessment Platform for developers and startups.

## Overview

Tracera is a defensive website analysis and risk-assessment platform. Users submit a website URL, and Tracera safely observes the publicly accessible response, extracting structured signals from HTTP, TLS, cookies, HTML, and basic performance characteristics. A deterministic analysis engine identifies concrete configuration and quality issues, and a risk engine aggregates those signals into an overall score.

**Core Principle**: Tracera has three distinct layers:
1. **Deterministic analysis** - use rules when the answer is directly measurable
2. **Machine learning** - use ML only when learning from multiple signals provides value that a transparent rule cannot
3. **Language generation** - use an LLM later, if useful, only to explain already-verified findings

## Architecture Summary

```
User → Next.js Frontend → FastAPI API → URL Validator + SSRF Guard → Safe Collector
                                                                    ↓
                                                         Feature Extraction
                                                                    ↓
                                                         Rule Engine → Findings
                                                                    ↓
                                                         Risk Scoring → Report
                                                                    ↓
                                                         PostgreSQL
```

### Scan pipeline (current)

1. `POST /api/v1/scans` validates and canonicalizes the URL, then runs the scan synchronously and returns the completed result (the same shape as `GET /api/v1/scans/{id}`).
2. The URL validator enforces scheme (http/https), hostname sanity, and a destination-port allowlist before any network I/O.
3. The SSRF guard resolves every target and blocks private, loopback, link-local, CGNAT, benchmark, 6to4, NAT64, and IPv4-mapped addresses (IPv4 and IPv6).
4. The collector pins each request to the validated IP (`Host` header + SNI), revalidates every redirect hop through the same guard, and enforces time/size/redirect budgets. A redirect to a blocked IP, port, or scheme is refused.
5. Features are extracted from the observed response; the deterministic rule engine produces evidence-backed findings; the risk engine aggregates a score.
6. The scan, findings, and response metadata (status code, response time, redirects, body size, final URL) are persisted in PostgreSQL.

## Repository Layout

```
tracera/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/v1/         # API routes
│   │   ├── core/           # Core configuration
│   │   ├── collector/      # HTTP collector
│   │   ├── features/       # Feature extraction
│   │   ├── rules/          # Rule engine
│   │   ├── scoring/        # Risk scoring
│   │   ├── reports/        # Report generation
│   │   ├── db/             # Database models
│   │   └── main.py         # Application entry
│   ├── tests/              # Test suite
│   └── requirements.txt
├── frontend/               # Next.js frontend
│   ├── app/                # App Router pages
│   ├── components/         # React components
│   ├── hooks/              # Custom hooks
│   ├── lib/                # Utilities
│   ├── services/           # API services
│   ├── public/             # Static assets
│   ├── styles/             # Global styles
│   ├── types/              # TypeScript types
│   ├── tests/              # Test suite
│   └── package.json
├── docs/                   # Documentation
├── scripts/                # Utility scripts
├── .env.example            # Environment template
├── .gitignore
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL (required; scans and history are persisted)

### Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head        # apply database migrations
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at `http://localhost:8000`

### Frontend Setup

```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
```

Frontend will be available at `http://localhost:3000`

### Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Key variables:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection URL |
| `CORS_ORIGINS` | JSON array of allowed frontend origins |
| `SCANNER_*` | Collector resource limits (timeouts, body size, redirects, port allowlist) |
| `SCAN_RATE_LIMIT_*` | Scan-creation rate limiting |
| `NEXT_PUBLIC_API_URL` | Base URL the frontend uses for API calls |

## API

Base URL: `http://localhost:8000/api/v1`

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Liveness/health check (also `GET /api/v1/health`) |
| `POST /scans` | Create and run a scan for a URL (synchronous; returns the completed scan) |
| `GET /scans` | List scans with pagination (`limit` ≤ 100, `offset`), `status`/`tier`/`search` filters |
| `GET /scans/{id}` | Fetch one scan with its findings |
| `GET /scans/{id}/export` | Download the scan report as a JSON attachment |

Scan creation is rate limited per client IP; exceeding the limit returns `429` with `Retry-After`.

## Commands

### Backend

| Command | Description |
|---------|-------------|
| `uvicorn app.main:app --reload` | Start development server |
| `pytest` | Run tests |
| `ruff check .` | Lint code |
| `black .` | Format code |

### Frontend

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server |
| `npm run build` | Build for production |
| `npm run start` | Start production server |
| `npm run lint` | Lint code |
| `npm run typecheck` | TypeScript type check (`tsc --noEmit`) |
| `npm test` | Run Jest tests |
| `npm run format` | Format code with Prettier |

### Testing

```bash
# Backend (from backend/, with the venv active; requires the local PostgreSQL)
pytest

# Frontend (from frontend/)
npm run typecheck
npm test
npm run build
```

## Current Status

- [x] Backend skeleton with FastAPI, frontend skeleton with Next.js + TypeScript
- [x] Health endpoints
- [x] URL validation, SSRF protection, and safe HTTP collector with resource limits
- [x] Scan API (`POST /api/v1/scans`, list/get/export) with persistence, filters, pagination, rate limiting
- [x] Feature extraction, deterministic rule engine, risk scoring
- [x] PostgreSQL integration with SQLAlchemy/Alembic migrations
- [x] Premium dark/light UI: landing page, dashboard, scan flow, scan results, history, printable report
- [x] JSON report export
- [ ] Authentication, projects, multi-tenancy (not implemented — see Security notes)
- [ ] ML-based scoring (deterministic baseline only; ML code exists but is not wired into the scan path)

## Security Notes

Tracera scans arbitrary URLs on request, so SSRF is the primary threat model. Current controls:

- **URL validation**: scheme allowlist (http/https), hostname sanity checks, destination-port allowlist (`SCANNER_ALLOWED_PORTS`, default `[80, 443, 8080, 8443]`).
- **IP blocking**: resolved targets are checked against blocked networks — loopback, RFC 1918, link-local, CGNAT (100.64.0.0/10), benchmark (198.18.0.0/15), 6to4 relay (192.88.99.0/24), NAT64, and IPv4-mapped IPv6 — for both address families.
- **DNS-rebinding mitigation**: each request is pinned to the validated IP address (via rewritten URL + `Host` header + SNI hostname), so a second DNS lookup cannot silently redirect the connection to an internal host.
- **Redirect revalidation**: every redirect hop is re-run through the full validation and IP-blocking pipeline; unsafe redirects are refused.
- **Resource limits**: per-request and total wall-clock timeouts, maximum response body size, and maximum redirect count per scan.
- **Rate limiting**: scan creation is limited per client IP (`SCAN_RATE_LIMIT_*`); the limiter is in-memory and per worker process.
- **Global error handling**: unhandled exceptions return a generic 500 without leaking internals.

### Limitations and residual risks

- **No authentication.** Anyone who can reach the API can create scans and read all scan history. Do not expose this instance to the public internet without adding auth (and per-tenant data isolation) first.
- **In-memory rate limiter** is per worker process and resets on restart; use a shared store (e.g., Redis) for multi-worker or multi-host deployments.
- **DNS pinning covers A/AAAA resolution** at scan start; TLS identity is verified against the original hostname via SNI, but exotic DNS setups (e.g., rebinding between CNAME chains after validation) are not individually re-resolved.
- **Passive scanning only.** Tracera sends normal GET requests and never attempts exploitation; absence of findings is not a guarantee of security.
- **Risk score is a fixed deterministic baseline** ("Score source: fixed baseline" in the UI); it is not ML-derived and thresholds may change as the rule set evolves.
- **CORS is an allowlist** but the API has no CSRF protection beyond it; again, do not deploy publicly without auth.

## Development

### Code Quality

**Backend**: Ruff (linting), Black (formatting), pytest (testing)
**Frontend**: ESLint (linting), Prettier (formatting), Jest (testing)

### Git Workflow

- Work on feature branches
- Create pull requests for review
- Require review from the other maintainer
- Merge to main after approval

## License

MIT