from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from qdrant_loader.config.state import StateManagementConfig
from qdrant_loader.core.state.models import Base
from qdrant_loader.core.state.utils import generate_sqlite_aiosqlite_url as _gen_url


def initialize_engine_and_session(
    config: StateManagementConfig,
) -> tuple[AsyncEngine, async_sessionmaker]:
    """Create the async engine and session factory for state DB.

    Uses the same engine configuration as StateManager did previously.
    """
    database_url = _gen_url(config.database_path)
    engine = create_async_engine(
        database_url,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return engine, session_factory


async def create_tables(engine: AsyncEngine) -> None:
    """Create database tables if they do not exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_engine(engine: AsyncEngine) -> None:
    """Dispose the async engine and free resources."""
    await engine.dispose()
