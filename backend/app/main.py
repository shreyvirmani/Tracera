from fastapi import FastAPI

from app.api.v1 import datasets, scans

app = FastAPI(title="Tracera API", version="0.1.0")

app.include_router(scans.router, prefix="/api/v1")
app.include_router(datasets.router, prefix="/api/v1")


@app.get("/")
async def root() -> dict:
    return {"service": "tracera-api", "status": "ok"}


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy"}
