from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.db.session import init_db, close_db
from app.api.v1 import datasets, scans


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title="Tracera API",
    description="Defensive website risk assessment platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scans.router, prefix="/api/v1")
app.include_router(datasets.router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "tracera-api"}


@app.get("/")
async def root():
    return {"message": "Tracera API", "docs": "/docs"}