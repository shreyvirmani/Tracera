from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dataset.models import DatasetSampleModel, DatasetVersionModel, ModelVersionModel


async def create_dataset_version(
    db: AsyncSession,
    version: str,
    feature_schema_version: str,
    description: str | None = None,
) -> DatasetVersionModel:
    dv = DatasetVersionModel(
        version=version,
        feature_schema_version=feature_schema_version,
        description=description,
    )
    db.add(dv)
    await db.commit()
    await db.refresh(dv)
    return dv


async def get_dataset_version(db: AsyncSession, version: str) -> DatasetVersionModel | None:
    result = await db.execute(
        select(DatasetVersionModel).where(DatasetVersionModel.version == version)
    )
    return result.scalar_one_or_none()


async def get_latest_dataset_version(db: AsyncSession) -> DatasetVersionModel | None:
    result = await db.execute(
        select(DatasetVersionModel).order_by(DatasetVersionModel.created_at.desc()).limit(1)
    )
    return result.scalar_one_or_none()


async def list_dataset_versions(
    db: AsyncSession, limit: int = 20, offset: int = 0
) -> list[DatasetVersionModel]:
    result = await db.execute(
        select(DatasetVersionModel)
        .order_by(DatasetVersionModel.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def bulk_insert_samples(db: AsyncSession, version_id: UUID, samples: list[dict]) -> int:
    sample_models = [
        DatasetSampleModel(
            dataset_version_id=version_id,
            feature_vector=s["feature_vector"],
            risk_tier=s["risk_tier"],
            risk_score=s["risk_score"],
            metadata_json=s["metadata"],
            split=s.get("split", "").lower() if s.get("split") else None,
        )
        for s in samples
    ]
    db.add_all(sample_models)
    await db.commit()
    return len(sample_models)


async def get_samples_by_split(
    db: AsyncSession,
    version_id: UUID,
    split: str,
    limit: int | None = None,
    offset: int = 0,
) -> list[DatasetSampleModel]:
    split_lower = split.lower()
    query = (
        select(DatasetSampleModel)
        .where(DatasetSampleModel.dataset_version_id == version_id)
        .where(DatasetSampleModel.split == split_lower)
        .order_by(DatasetSampleModel.created_at)
    )
    if limit:
        query = query.limit(limit)
    query = query.offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_sample_counts_by_split(db: AsyncSession, version_id: UUID) -> dict:
    result = await db.execute(
        select(DatasetSampleModel.split, func.count(DatasetSampleModel.id))
        .where(DatasetSampleModel.dataset_version_id == version_id)
        .group_by(DatasetSampleModel.split)
    )
    return {row.split: row[1] for row in result.all()}


async def create_model_version(
    db: AsyncSession,
    model_version: str,
    dataset_version: str,
    feature_schema_version: str,
    algorithm: str,
    hyperparameters: dict,
    metrics: dict,
    notes: str | None = None,
) -> ModelVersionModel:
    mv = ModelVersionModel(
        model_version=model_version,
        dataset_version=dataset_version,
        feature_schema_version=feature_schema_version,
        algorithm=algorithm,
        hyperparameters=hyperparameters,
        metrics=metrics,
        notes=notes,
    )
    db.add(mv)
    await db.commit()
    await db.refresh(mv)
    return mv


async def get_model_version(db: AsyncSession, model_version: str) -> ModelVersionModel | None:
    result = await db.execute(
        select(ModelVersionModel).where(ModelVersionModel.model_version == model_version)
    )
    return result.scalar_one_or_none()


async def list_model_versions(
    db: AsyncSession, limit: int = 20, offset: int = 0
) -> list[ModelVersionModel]:
    result = await db.execute(
        select(ModelVersionModel)
        .order_by(ModelVersionModel.trained_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())
