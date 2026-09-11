from fastapi import FastAPI

app = FastAPI(title="Tracera API", version="0.1.0")


@app.get("/")
async def root() -> dict:
    return {"service": "tracera-api", "status": "ok"}


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy"}
