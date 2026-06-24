from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from qdrant_loader.config.state import StateManagementConfig
from qdrant_loader.core.state.models import Base
from qdrant_loader.core.state.utils import generate_database_url


def initialize_engine_and_session(
    config: StateManagementConfig,
) -> tuple[AsyncEngine, async_sessionmaker]:
    """Create the async engine and session factory for the state DB.

    SQLite uses a StaticPool with check_same_thread disabled (single in-process
    file/memory DB). PostgreSQL uses a real connection pool sized from
    config.connection_pool, with pool_pre_ping so RDS idle-connection drops are
    detected and recycled rather than surfacing as errors.
    """
    database_url = generate_database_url(config)

    if database_url.startswith("sqlite"):
        engine = create_async_engine(
            database_url,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
            echo=False,
        )
    else:
        pool = config.connection_pool or {}
        engine = create_async_engine(
            database_url,
            pool_size=pool.get("size", 5),
            pool_timeout=pool.get("timeout", 30),
            pool_pre_ping=True,
            pool_recycle=1800,  # recycle connections every 30 min (RDS-friendly)
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
