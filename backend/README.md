# Tracera Backend

FastAPI-based backend for the Tracera website risk assessment platform.

## Requirements

- Python 3.12+
- uv or pip

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Development

```bash
# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest

# Lint
ruff check .

# Format
black .
```

## API Endpoints

- `GET /` - Service info
- `GET /health` - Health check

## Project Structure

```
backend/
├── app/
│   ├── api/v1/          # API routes
│   ├── core/            # Core configuration
│   ├── collector/       # HTTP collector
│   ├── features/        # Feature extraction
│   ├── rules/           # Rule engine
│   ├── scoring/         # Risk scoring
│   ├── reports/         # Report generation
│   ├── db/              # Database models
│   └── main.py          # Application entry
├── tests/               # Test suite
└── requirements.txt     # Dependencies
```