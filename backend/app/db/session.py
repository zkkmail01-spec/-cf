from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


settings = get_settings()
engine = create_async_engine(settings.database_url, pool_pre_ping=True) if settings.storage_backend == "sql" else None
SessionFactory = async_sessionmaker(engine, expire_on_commit=False) if engine is not None else None


async def get_session() -> AsyncIterator[AsyncSession]:
    if SessionFactory is None:
        raise RuntimeError("SQL session is unavailable when STORAGE_BACKEND=cloudbase")
    async with SessionFactory() as session:
        yield session
