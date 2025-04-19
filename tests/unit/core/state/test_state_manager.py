"""
Unit tests for state manager.
"""

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.sql import select

from qdrant_loader.core.state.models import Base, DocumentStateRecord, IngestionHistory
from qdrant_loader.core.state.state_manager import StateManager


@pytest_asyncio.fixture
async def async_engine(test_global_config):
    """Create an async engine for testing."""
    db_url = test_global_config.state_management.database_path
    if not db_url.startswith("sqlite:///"):
        db_url = f"sqlite:///{db_url}"

    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_url.replace('sqlite:///', '')}",
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def async_session_factory(async_engine):
    """Create an async session factory for testing."""
    return async_sessionmaker(async_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def state_manager(test_global_config, async_engine):
    """Create test state manager with async engine."""
    manager = StateManager(test_global_config.state_management)
    manager.engine = async_engine
    manager.AsyncSession = async_sessionmaker(async_engine, expire_on_commit=False)
    return manager


@pytest.mark.asyncio
async def test_ingestion_history_creation(state_manager):
    """Test creating an ingestion history record."""
    async with state_manager.AsyncSession() as session:
        now = datetime.now(UTC)
        history = IngestionHistory(
            source_type="test",
            source="test-source",
            last_successful_ingestion=now,
            status="completed",
            document_count=1,
            error_message=None,
            created_at=now,
            updated_at=now,
        )
        session.add(history)
        await session.commit()
        assert history.id is not None


@pytest.mark.asyncio
async def test_document_state_creation(state_manager):
    """Test creating a document state record."""
    async with state_manager.AsyncSession() as session:
        now = datetime.now(UTC)
        doc_state = DocumentStateRecord(
            source_type="test",
            source="test-source",
            document_id="doc-1",
            last_updated=now,
            last_ingested=now,
            is_deleted=False,
            created_at=now,
            updated_at=now,
        )
        session.add(doc_state)
        await session.commit()
        assert doc_state.id is not None


@pytest.mark.asyncio
async def test_get_document_state(state_manager):
    """Test retrieving a document state."""
    async with state_manager.AsyncSession() as session:
        now = datetime.now(UTC)
        doc_state = DocumentStateRecord(
            source_type="test",
            source="test-source",
            document_id="doc-1",
            last_updated=now,
            last_ingested=now,
            is_deleted=False,
            created_at=now,
            updated_at=now,
        )
        session.add(doc_state)
        await session.commit()

        result = await session.execute(select(DocumentStateRecord).filter_by(id=doc_state.id))
        retrieved = result.scalar_one_or_none()
        assert retrieved is not None
        assert retrieved.source_type == "test"
        assert retrieved.document_id == "doc-1"


@pytest.mark.asyncio
async def test_update_document_state(state_manager):
    """Test updating a document state."""
    async with state_manager.AsyncSession() as session:
        now = datetime.now(UTC)
        doc_state = DocumentStateRecord(
            source_type="test",
            source="test-source",
            document_id="doc-1",
            last_updated=now,
            last_ingested=now,
            is_deleted=False,
            created_at=now,
            updated_at=now,
        )
        session.add(doc_state)
        await session.commit()

        # Update the document state
        doc_state.is_deleted = True  # type: ignore
        await session.commit()

        result = await session.execute(select(DocumentStateRecord).filter_by(id=doc_state.id))
        updated = result.scalar_one_or_none()
        assert updated is not None
        assert updated.is_deleted is True
