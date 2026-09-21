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
- PostgreSQL (for later phases)

### Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at `http://localhost:8000`

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend will be available at `http://localhost:3000`

### Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

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
| `npm run format` | Format code with Prettier |

## Current Status (Phase 1 - Bootstrap)

- [x] Backend skeleton with FastAPI
- [x] Frontend skeleton with Next.js + TypeScript
- [x] Basic health endpoints (`GET /`, `GET /health`)
- [x] Home page displaying project name and status
- [x] Environment configuration template
- [x] Linting and formatting setup (Ruff, Black, ESLint, Prettier)

## Future Roadmap

### Phase 1 - Safe Scanner (Next)
- URL validation and canonicalization
- SSRF protection (DNS/IP validation, private range blocking)
- Safe HTTP collector with timeouts and size limits
- Basic scan API endpoint (`POST /api/v1/scans`)

### Phase 2 - Feature Extraction
- HTTP features (status, headers, timing, redirects)
- TLS metadata extraction
- Cookie parsing and analysis
- HTML structure analysis
- Versioned feature schema

### Phase 3 - Rule Engine
- 10-15 deterministic security/configuration rules
- Evidence-backed findings
- Recommendations per finding
- Unit tests for each rule

### Phase 4 - Database + Dashboard
- PostgreSQL integration with SQLAlchemy/Alembic
- Scan and findings persistence
- Basic dashboard UI
- End-to-end scan flow

### Phase 5+ - ML & Advanced Features
- Dataset construction and labeling
- Classical ML baselines (Logistic Regression, Random Forest)
- ML go/no-go evaluation gate
- CVE correlation
- Authentication and projects
- Scan history and comparison

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