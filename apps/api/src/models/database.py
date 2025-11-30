"""
Database connection and session management.
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)

from src.core.config import settings

# Create async engine
engine = create_async_engine(
    str(settings.database.url),
    echo=settings.database.echo,
    pool_size=settings.database.pool_size,
    max_overflow=settings.database.pool_overflow,
    pool_timeout=settings.database.pool_timeout,
)

# Session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Initialize database (create tables)."""
    from .base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
