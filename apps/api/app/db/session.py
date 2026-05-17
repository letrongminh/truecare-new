from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings


LOCAL_DATABASE_URL = "postgresql+asyncpg://truecare:truecare@127.0.0.1:55432/truecare"


def normalize_database_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url.removeprefix("postgresql://")
    return url


def configured_database_url() -> str:
    settings = get_settings()
    return normalize_database_url(settings.database_url_pooler or settings.database_url_direct or LOCAL_DATABASE_URL)


@lru_cache
def get_engine(url: str | None = None) -> AsyncEngine:
    return create_async_engine(normalize_database_url(url or configured_database_url()), pool_pre_ping=True, poolclass=NullPool)


@lru_cache
def get_sessionmaker(url: str | None = None) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(url), expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with get_sessionmaker()() as session:
        yield session


async def set_local_context(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    user_id: UUID | None = None,
    role: str | None = None,
) -> None:
    values = {
        "app.current_tenant": str(tenant_id),
        "app.current_user": str(user_id) if user_id else "",
        "app.current_role": role or "",
    }
    for key, value in values.items():
        await session.execute(text("select set_config(:key, :value, true)"), {"key": key, "value": value})
