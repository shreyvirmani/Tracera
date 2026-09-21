from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings

# Lazy initialization to avoid import-time asyncpg requirement
_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.db_echo,
            poolclass=NullPool,
        )
    return _engine


def get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def get_db() -> AsyncSession:
    async with get_session_factory()() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    from app.db.models import Base
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None