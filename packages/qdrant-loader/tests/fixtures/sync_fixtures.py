"""
Pytest fixtures for sync testing infrastructure.

Provides database setup/teardown, mock configurations, and test data.
"""

import asyncio
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

from qdrant_loader.config import ConfigurationManager
from qdrant_loader.core.managers.qdrant_manager import QdrantManager
from qdrant_loader.core.managers.neo4j_manager import Neo4jManager
from qdrant_loader.core.managers.graphiti_manager import GraphitiManager
from qdrant_loader.core.sync.types import SyncOperationType, SyncOperationStatus


@pytest.fixture
def sync_test_config() -> Dict[str, Any]:
    """Provide test configuration for sync components."""
    return {
        "qdrant": {
            "host": "localhost",
            "port": 6333,
            "collection_name": "test_collection",
            "vector_size": 384,
            "distance": "Cosine",
        },
        "neo4j": {
            "uri": "bolt://localhost:7687",
            "username": "neo4j",
            "password": "test_password",
            "database": "test_db",
        },
        "graphiti": {
            "enabled": True,
            "llm_provider": "openai",
            "model": "gpt-3.5-turbo",
        },
        "sync": {
            "batch_size": 10,
            "max_retries": 3,
            "timeout_seconds": 30,
            "enable_monitoring": True,
            "enable_conflict_resolution": True,
        },
    }


@pytest.fixture
async def mock_qdrant_manager() -> AsyncGenerator[AsyncMock, None]:
    """Provide mock QdrantManager for testing."""
    mock_manager = AsyncMock(spec=QdrantManager)

    # Configure common mock behaviors
    mock_manager.upsert_points.return_value = True
    mock_manager.delete_points.return_value = True
    mock_manager.search.return_value = []
    mock_manager.get_point.return_value = None
    mock_manager.health_check.return_value = True

    yield mock_manager


@pytest.fixture
async def mock_neo4j_manager() -> AsyncGenerator[AsyncMock, None]:
    """Provide mock Neo4jManager for testing."""
    mock_manager = AsyncMock(spec=Neo4jManager)

    # Configure common mock behaviors
    mock_manager.create_node.return_value = {"id": "test_node_id"}
    mock_manager.update_node.return_value = True
    mock_manager.delete_node.return_value = True
    mock_manager.execute_query.return_value = []
    mock_manager.health_check.return_value = True

    yield mock_manager


@pytest.fixture
async def mock_graphiti_manager() -> AsyncGenerator[AsyncMock, None]:
    """Provide mock GraphitiManager for testing."""
    mock_manager = AsyncMock(spec=GraphitiManager)

    # Configure common mock behaviors
    mock_manager.extract_entities.return_value = []
    mock_manager.create_episode.return_value = {"id": "test_episode_id"}
    mock_manager.invalidate_edges.return_value = True
    mock_manager.health_check.return_value = True

    yield mock_manager


@pytest.fixture
async def test_database_setup(
    sync_test_config: Dict[str, Any],
) -> AsyncGenerator[Dict[str, Any], None]:
    """Set up test databases and provide cleanup."""
    # Create temporary directories for test data
    temp_dir = Path(tempfile.mkdtemp(prefix="sync_test_"))

    setup_info = {"temp_dir": temp_dir, "config": sync_test_config, "initialized": True}

    try:
        yield setup_info
    finally:
        # Cleanup
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


@pytest.fixture
def cleanup_test_data():
    """Provide cleanup utilities for test data."""
    cleanup_tasks = []

    def add_cleanup(task):
        cleanup_tasks.append(task)

    yield add_cleanup

    # Execute cleanup tasks
    for task in cleanup_tasks:
        try:
            if asyncio.iscoroutinefunction(task):
                asyncio.run(task())
            else:
                task()
        except Exception as e:
            print(f"Cleanup task failed: {e}")


@pytest.fixture
async def test_configuration_manager(
    sync_test_config: Dict[str, Any],
) -> AsyncGenerator[ConfigurationManager, None]:
    """Provide test configuration manager."""
    # Create temporary config files
    temp_dir = Path(tempfile.mkdtemp(prefix="config_test_"))

    try:
        config_manager = ConfigurationManager()
        # Mock the configuration loading
        config_manager._config = sync_test_config

        yield config_manager
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


@pytest.fixture
def mock_atomic_transaction():
    """Provide mock atomic transaction for testing."""
    mock_transaction = MagicMock()
    mock_transaction.commit = AsyncMock(return_value=True)
    mock_transaction.rollback = AsyncMock(return_value=True)
    mock_transaction.add_operation = MagicMock()
    mock_transaction.__aenter__ = AsyncMock(return_value=mock_transaction)
    mock_transaction.__aexit__ = AsyncMock(return_value=None)

    return mock_transaction


@pytest.fixture
def mock_sync_operation():
    """Provide mock sync operation for testing."""
    return {
        "operation_id": "test_op_123",
        "operation_type": SyncOperationType.CREATE_DOCUMENT,
        "entity_id": "test_entity_123",
        "entity_type": "document",
        "status": SyncOperationStatus.PENDING,
        "data": {"content": "test content", "title": "test title"},
        "metadata": {"source": "test", "timestamp": "2024-01-01T00:00:00Z"},
    }


@pytest.fixture
def sample_document_data():
    """Provide sample document data for testing."""
    return {
        "id": "doc_123",
        "title": "Test Document",
        "content": "This is test content for synchronization testing.",
        "metadata": {
            "author": "test_user",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "source": "test_source",
            "tags": ["test", "sync", "document"],
        },
        "embedding": [0.1] * 384,  # Mock embedding vector
    }


@pytest.fixture
def sample_entity_data():
    """Provide sample entity data for testing."""
    return {
        "id": "entity_123",
        "type": "Person",
        "properties": {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "department": "Engineering",
        },
        "relationships": [
            {
                "type": "WORKS_IN",
                "target_id": "dept_123",
                "properties": {"since": "2023-01-01"},
            }
        ],
    }
