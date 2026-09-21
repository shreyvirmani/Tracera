from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dataset.generator import generate_balanced_dataset, generate_dataset
from app.dataset.repository import (
    bulk_insert_samples,
    create_dataset_version,
    create_model_version,
    get_dataset_version,
    get_model_version,
    get_sample_counts_by_split,
    get_samples_by_split,
    list_dataset_versions,
    list_model_versions,
)
from app.db.session import get_db

router = APIRouter(prefix="/datasets", tags=["datasets"])


class CreateDatasetRequest(BaseModel):
    version: str = Field(..., pattern=r"^v?\d+\.\d+\.\d+$")
    description: str | None = None
    n_samples: int = Field(default=1000, ge=100, le=100000)
    balanced: bool = False
    n_per_tier: int | None = None
    family_distribution: dict | None = None


class CreateDatasetResponse(BaseModel):
    version: str
    total_samples: int
    train_samples: int
    val_samples: int
    test_samples: int
    label_distribution: dict


@router.post("", response_model=CreateDatasetResponse, status_code=status.HTTP_201_CREATED)
async def create_dataset(
    request: CreateDatasetRequest,
    db: AsyncSession = Depends(get_db),
) -> CreateDatasetResponse:
    existing = await get_dataset_version(db, request.version)
    if existing:
        raise HTTPException(
            status_code=409, detail=f"Dataset version {request.version} already exists"
        )

    dv = await create_dataset_version(
        db=db,
        version=request.version,
        feature_schema_version="features-v1",
        description=request.description,
    )

    if request.balanced:
        n_per_tier = request.n_per_tier or (request.n_samples // 4)
        dataset = generate_balanced_dataset(request.version, n_per_tier)
    else:
        dataset = generate_dataset(
            version=request.version,
            n_samples=request.n_samples,
            description=request.description,
            family_distribution=request.family_distribution,
        )

    samples_data = [
        {
            "feature_vector": sample.feature_vector,
            "risk_tier": sample.risk_tier.value,
            "risk_score": sample.risk_score,
            "metadata": sample.metadata.model_dump(mode="json"),
            "split": sample.split.lower() if sample.split else None,
        }
        for sample in dataset.samples
    ]

    await bulk_insert_samples(db, dv.id, samples_data)

    return CreateDatasetResponse(
        version=dataset.version.version,
        total_samples=dataset.version.total_samples,
        train_samples=dataset.version.train_samples,
        val_samples=dataset.version.val_samples,
        test_samples=dataset.version.test_samples,
        label_distribution=dataset.version.label_distribution,
    )


class DatasetVersionResponse(BaseModel):
    version: str
    feature_schema_version: str
    description: str | None
    total_samples: int
    train_samples: int
    val_samples: int
    test_samples: int
    label_distribution: dict
    created_at: str


class CreateModelRequest(BaseModel):
    model_version: str = Field(..., pattern=r"^v?\d+\.\d+\.\d+$")
    dataset_version: str
    algorithm: str = Field(..., pattern="^(logistic_regression|random_forest|xgboost)$")
    hyperparameters: dict = Field(default_factory=dict)
    metrics: dict = Field(default_factory=dict)
    notes: str | None = None


@router.post("/models", status_code=status.HTTP_201_CREATED)
async def create_model(
    request: CreateModelRequest,
    db: AsyncSession = Depends(get_db),
):
    dv = await get_dataset_version(db, request.dataset_version)
    if not dv:
        raise HTTPException(status_code=404, detail="Dataset version not found")

    mv = await create_model_version(
        db=db,
        model_version=request.model_version,
        dataset_version=request.dataset_version,
        feature_schema_version="features-v1",
        algorithm=request.algorithm,
        hyperparameters=request.hyperparameters,
        metrics=request.metrics,
        notes=request.notes,
    )
    return {"model_version": mv.model_version, "created_at": mv.trained_at.isoformat()}


@router.get("/models", response_model=list[dict])
async def list_models(
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    models = await list_model_versions(db, limit, offset)
    return [
        {
            "model_version": m.model_version,
            "dataset_version": m.dataset_version,
            "algorithm": m.algorithm,
            "metrics": m.metrics,
            "trained_at": m.trained_at.isoformat(),
        }
        for m in models
    ]


@router.get("/models/{model_version}", response_model=dict)
async def get_model(
    model_version: str,
    db: AsyncSession = Depends(get_db),
):
    mv = await get_model_version(db, model_version)
    if not mv:
        raise HTTPException(status_code=404, detail="Model version not found")
    return {
        "model_version": mv.model_version,
        "dataset_version": mv.dataset_version,
        "feature_schema_version": mv.feature_schema_version,
        "algorithm": mv.algorithm,
        "hyperparameters": mv.hyperparameters,
        "metrics": mv.metrics,
        "notes": mv.notes,
        "trained_at": mv.trained_at.isoformat(),
    }


@router.get("", response_model=list[DatasetVersionResponse])
async def list_datasets(
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[DatasetVersionResponse]:
    versions = await list_dataset_versions(db, limit, offset)
    return [
        DatasetVersionResponse(
            version=v.version,
            feature_schema_version=v.feature_schema_version,
            description=v.description,
            total_samples=v.total_samples,
            train_samples=v.train_samples,
            val_samples=v.val_samples,
            test_samples=v.test_samples,
            label_distribution=v.label_distribution,
            created_at=v.created_at.isoformat(),
        )
        for v in versions
    ]


@router.get("/{version}", response_model=DatasetVersionResponse)
async def get_dataset(
    version: str,
    db: AsyncSession = Depends(get_db),
) -> DatasetVersionResponse:
    dv = await get_dataset_version(db, version)
    if not dv:
        raise HTTPException(status_code=404, detail="Dataset version not found")
    return DatasetVersionResponse(
        version=dv.version,
        feature_schema_version=dv.feature_schema_version,
        description=dv.description,
        total_samples=dv.total_samples,
        train_samples=dv.train_samples,
        val_samples=dv.val_samples,
        test_samples=dv.test_samples,
        label_distribution=dv.label_distribution,
        created_at=dv.created_at.isoformat(),
    )


class SampleResponse(BaseModel):
    id: str
    risk_tier: str
    risk_score: int
    metadata: dict
    split: str | None


@router.get("/{version}/samples", response_model=list[SampleResponse])
async def get_dataset_samples(
    version: str,
    split: str | None = Query(default=None, pattern="^(train|validation|test)$"),
    limit: int = Query(default=50, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[SampleResponse]:
    dv = await get_dataset_version(db, version)
    if not dv:
        raise HTTPException(status_code=404, detail="Dataset version not found")

    split_filter = split.lower() if split else None
    samples = await get_samples_by_split(
        db, dv.id, (split_filter or "train").lower(), limit, offset
    )
    return [
        SampleResponse(
            id=str(s.id),
            risk_tier=s.risk_tier.value,
            risk_score=s.risk_score,
            metadata=s.metadata_json,
            split=s.split if s.split else None,
        )
        for s in samples
    ]


@router.get("/{version}/stats")
async def get_dataset_stats(
    version: str,
    db: AsyncSession = Depends(get_db),
):
    dv = await get_dataset_version(db, version)
    if not dv:
        raise HTTPException(status_code=404, detail="Dataset version not found")

    counts = await get_sample_counts_by_split(db, dv.id)
    return {
        "version": dv.version,
        "total_samples": dv.total_samples,
        "train_samples": dv.train_samples,
        "val_samples": dv.val_samples,
        "test_samples": dv.test_samples,
        "label_distribution": dv.label_distribution,
        "split_counts": counts,
    }
