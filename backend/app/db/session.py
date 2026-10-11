from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.storage.factory import create_document_store


settings = get_settings()
engine = create_async_engine(settings.database_url, pool_pre_ping=True) if settings.storage_backend == "sql" else None
SessionFactory = async_sessionmaker(engine, expire_on_commit=False) if engine is not None else None


class DocumentSession:
    """Compatibility session passed to services when CloudBase is selected."""

    def __init__(self) -> None:
        self.store = create_document_store(settings)

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None

    async def flush(self) -> None:
        return None


async def get_session() -> AsyncIterator[AsyncSession | DocumentSession]:
    if SessionFactory is None:
        yield DocumentSession()
        return
    async with SessionFactory() as session:
        yield session
