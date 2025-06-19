"""Integration test configuration.

This conftest.py ensures that test environment variables are loaded
before any module-level configuration checks are performed.
"""

from pathlib import Path
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio
from dotenv import load_dotenv

from qdrant_loader.core.managers.neo4j_manager import Neo4jManager
from qdrant_loader.core.managers.qdrant_manager import QdrantManager
from qdrant_loader.core.managers.id_mapping_manager import IDMappingManager, MappingType
from qdrant_loader.core.types import EntityType, TemporalInfo


# Load environment variables at import time
tests_dir = Path(__file__).parent.parent
env_path = tests_dir / ".env.test"
if env_path.exists():
    load_dotenv(env_path, override=True)


class TestConfig:
    """Test configuration object with attribute access."""

    def __init__(self, config_dict: dict[str, Any]):
        for key, value in config_dict.items():
            if isinstance(value, dict):
                setattr(self, key, TestConfig(value))
            else:
                setattr(self, key, value)


@pytest.fixture
def test_config() -> TestConfig:
    """Provide test configuration for integration tests."""
    config_dict = {
        "qdrant": {
            "host": "localhost",
            "port": 6333,
            "collection_name": "test_collection",
            "vector_size": 384,
            "distance": "Cosine",
            "api_key": None,
        },
        "neo4j": {
            "uri": "bolt://localhost:7687",
            "username": "neo4j",
            "password": "test_password",
            "database": "test_db",
        },
        "graphiti": {
            "enabled": True,
            "llm": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "api_key": "test-key",
                "max_tokens": 4000,
                "temperature": 0.1,
            },
            "embedder": {
                "provider": "openai",
                "model": "text-embedding-3-small",
                "api_key": "test-key",
                "dimensions": None,
                "batch_size": 100,
            },
            "operational": {
                "max_episode_length": 10000,
                "search_limit_default": 10,
                "search_limit_max": 100,
                "enable_auto_indexing": True,
                "enable_constraints": True,
                "timeout_seconds": 30,
            },
            "debug_mode": False,
        },
        "sync": {
            "batch_size": 10,
            "max_retries": 3,
            "timeout_seconds": 30,
            "enable_monitoring": True,
            "enable_conflict_resolution": True,
        },
        "embedding": {
            "api_key": "test-key",
            "model": "text-embedding-ada-002",
        },
    }
    return TestConfig(config_dict)


@pytest_asyncio.fixture
async def qdrant_manager() -> AsyncGenerator[AsyncMock, None]:
    """Provide mock QdrantManager for integration testing."""
    mock_manager = AsyncMock(spec=QdrantManager)

    # Configure common mock behaviors
    mock_manager.upsert_points.return_value = True
    mock_manager.delete_points.return_value = True
    mock_manager.search.return_value = []
    mock_manager.health_check.return_value = True
    mock_manager.create_collection.return_value = True
    mock_manager.delete_collection.return_value = True

    # Mock the _ensure_client_connected method to return a mock client
    mock_client = AsyncMock()

    # Create a mock point that will be returned by retrieve
    mock_point = AsyncMock()
    mock_point.id = "test_point_id"
    mock_point.payload = {
        "document_id": "test_doc_id",
        "content": "test content",
        "title": "Test Document",
    }

    mock_client.retrieve.return_value = [mock_point]
    mock_client.upsert.return_value = True
    mock_client.delete.return_value = True
    mock_manager._ensure_client_connected.return_value = mock_client

    yield mock_manager


@pytest_asyncio.fixture
async def id_mapping_manager() -> AsyncGenerator[AsyncMock, None]:
    """Provide mock IDMappingManager for integration testing."""
    mock_manager = AsyncMock(spec=IDMappingManager)

    # Store created mappings for dynamic responses
    created_mappings = {}
    mapping_counter = 1

    async def mock_create_mapping(
        qdrant_point_id=None,
        neo4j_node_id=None,
        neo4j_node_uuid=None,
        entity_type=None,
        mapping_type=None,
        entity_name=None,
        metadata=None,
        validate_existence=True,
    ):
        """Mock create_mapping with proper return values."""
        nonlocal mapping_counter

        mapping_id = f"mapping_{mapping_counter}"
        mapping_counter += 1

        # Create a mock mapping object
        mock_mapping = AsyncMock()
        mock_mapping.mapping_id = mapping_id
        mock_mapping.qdrant_point_id = qdrant_point_id
        mock_mapping.neo4j_node_id = neo4j_node_id
        mock_mapping.neo4j_node_uuid = neo4j_node_uuid or f"uuid_{mapping_id}"
        mock_mapping.entity_type = entity_type or EntityType.CONCEPT
        mock_mapping.mapping_type = mapping_type or MappingType.DOCUMENT
        mock_mapping.entity_name = entity_name
        mock_mapping.metadata = metadata or {}
        mock_mapping.document_version = 1
        mock_mapping.created_at = "2024-01-01T00:00:00Z"
        mock_mapping.updated_at = "2024-01-01T00:00:00Z"

        # Store the mapping for later retrieval
        created_mappings[mapping_id] = mock_mapping
        if qdrant_point_id:
            created_mappings[f"qdrant_{qdrant_point_id}"] = mock_mapping
        if neo4j_node_id:
            created_mappings[f"neo4j_{neo4j_node_id}"] = mock_mapping
        if neo4j_node_uuid:
            created_mappings[f"uuid_{neo4j_node_uuid}"] = mock_mapping

        return mock_mapping

    async def mock_get_mapping_by_qdrant_id(qdrant_id):
        """Mock get_mapping_by_qdrant_id."""
        return created_mappings.get(f"qdrant_{qdrant_id}")

    async def mock_get_mapping_by_neo4j_id(neo4j_id):
        """Mock get_mapping_by_neo4j_id."""
        return created_mappings.get(f"neo4j_{neo4j_id}")

    async def mock_get_mapping_by_neo4j_uuid(neo4j_uuid):
        """Mock get_mapping_by_neo4j_uuid."""
        return created_mappings.get(f"uuid_{neo4j_uuid}")

    async def mock_delete_mapping(mapping_id):
        """Mock delete_mapping."""
        # Remove from all lookup keys
        mapping = created_mappings.get(mapping_id)
        if mapping:
            if mapping.qdrant_point_id:
                created_mappings.pop(f"qdrant_{mapping.qdrant_point_id}", None)
            if mapping.neo4j_node_id:
                created_mappings.pop(f"neo4j_{mapping.neo4j_node_id}", None)
            if mapping.neo4j_node_uuid:
                created_mappings.pop(f"uuid_{mapping.neo4j_node_uuid}", None)
            created_mappings.pop(mapping_id, None)
        return True

    async def mock_update_document_version(*args, **kwargs):
        """Mock update_document_version."""
        return True

    async def mock_health_check():
        """Mock health_check."""
        return {"status": "healthy"}

    # Configure mock methods
    mock_manager.create_mapping.side_effect = mock_create_mapping
    mock_manager.get_mapping_by_qdrant_id.side_effect = mock_get_mapping_by_qdrant_id
    mock_manager.get_mapping_by_neo4j_id.side_effect = mock_get_mapping_by_neo4j_id
    mock_manager.get_mapping_by_neo4j_uuid.side_effect = mock_get_mapping_by_neo4j_uuid
    mock_manager.delete_mapping.side_effect = mock_delete_mapping
    mock_manager.update_document_version.side_effect = mock_update_document_version
    mock_manager.health_check.side_effect = mock_health_check

    yield mock_manager


@pytest_asyncio.fixture
async def neo4j_manager() -> AsyncGenerator[AsyncMock, None]:
    """Provide mock Neo4jManager for integration testing."""
    mock_manager = AsyncMock(spec=Neo4jManager)

    # Store created documents for dynamic responses
    created_documents = {}

    def mock_execute_query(query: str, parameters: dict | None = None, **kwargs):
        """Mock execute_query with dynamic responses based on query content."""
        if parameters is None:
            parameters = {}

        # Handle IDMapping queries
        if "IDMapping" in query:
            # Handle IDMapping creation/update (MERGE queries)
            if "MERGE" in query and "mapping_id" in parameters:
                mapping_id = parameters["mapping_id"]
                properties = parameters.get("properties", {})

                # Create a complete IDMapping data structure
                mapping_data = {
                    "mapping_id": mapping_id,
                    "qdrant_point_id": properties.get("qdrant_point_id"),
                    "neo4j_node_id": properties.get("neo4j_node_id"),
                    "neo4j_node_uuid": properties.get("neo4j_node_uuid"),
                    "entity_type": properties.get("entity_type", "concept"),
                    "mapping_type": properties.get("mapping_type", "document"),
                    "entity_name": properties.get("entity_name"),
                    "status": properties.get("status", "active"),
                    "metadata": properties.get("metadata", {}),
                    "temporal_info": properties.get(
                        "temporal_info",
                        {
                            "valid_from": "2024-01-01T00:00:00Z",
                            "valid_to": None,
                            "transaction_time": "2024-01-01T00:00:00Z",
                            "version": 1,
                        },
                    ),
                    "last_sync_time": properties.get("last_sync_time"),
                    "sync_version": properties.get("sync_version", 1),
                    "sync_errors": properties.get("sync_errors", []),
                    "document_version": properties.get("document_version", 1),
                    "last_update_time": properties.get("last_update_time"),
                    "created_time": properties.get(
                        "created_time", "2024-01-01T00:00:00Z"
                    ),
                    "update_source": properties.get("update_source"),
                    "content_hash": properties.get("content_hash"),
                    "version_history": properties.get("version_history", []),
                    "update_frequency": properties.get("update_frequency", 0),
                    "qdrant_exists": properties.get("qdrant_exists", True),
                    "neo4j_exists": properties.get("neo4j_exists", True),
                    "last_validation_time": properties.get("last_validation_time"),
                }

                # Store the mapping for later retrieval
                created_documents[f"mapping_{mapping_id}"] = mapping_data
                return [{"m": mapping_data}]

            # Handle IDMapping retrieval by qdrant_point_id
            elif "qdrant_point_id" in parameters:
                qdrant_point_id = parameters["qdrant_point_id"]
                # Look for existing mapping
                for key, data in created_documents.items():
                    if (
                        key.startswith("mapping_")
                        and data.get("qdrant_point_id") == qdrant_point_id
                    ):
                        return [{"m": data}]
                return []

            # Handle IDMapping retrieval by neo4j_node_id
            elif "neo4j_node_id" in parameters:
                neo4j_node_id = parameters["neo4j_node_id"]
                for key, data in created_documents.items():
                    if (
                        key.startswith("mapping_")
                        and data.get("neo4j_node_id") == neo4j_node_id
                    ):
                        return [{"m": data}]
                return []

            # Handle IDMapping retrieval by neo4j_node_uuid
            elif "neo4j_node_uuid" in parameters:
                neo4j_node_uuid = parameters["neo4j_node_uuid"]
                for key, data in created_documents.items():
                    if (
                        key.startswith("mapping_")
                        and data.get("neo4j_node_uuid") == neo4j_node_uuid
                    ):
                        return [{"m": data}]
                return []

            # Handle IDMapping retrieval by mapping_id
            elif "mapping_id" in parameters:
                mapping_id = parameters["mapping_id"]
                mapping_key = f"mapping_{mapping_id}"
                if mapping_key in created_documents:
                    return [{"m": created_documents[mapping_key]}]
                return []

        # Handle document creation (both CREATE and MERGE patterns)
        elif ("CREATE" in query and "document_id" in parameters) or (
            "MERGE" in query and "uuid" in parameters
        ):
            if "document_id" in parameters:
                # Direct document creation
                doc_id = parameters["document_id"]
                title = parameters.get("title", "Test Document")
                content = parameters.get("content", "test content")

                created_documents[doc_id] = {
                    "id": f"node_{doc_id}",
                    "document_id": doc_id,
                    "title": title,
                    "content": content,
                }
                return [{"d": created_documents[doc_id]}]
            elif "uuid" in parameters and "properties" in parameters:
                # Atomic transaction system MERGE pattern
                uuid_val = parameters["uuid"]
                props = parameters["properties"]

                # Extract document_id from properties if available
                doc_id = props.get("document_id", uuid_val)

                created_documents[doc_id] = {
                    "id": f"node_{uuid_val}",
                    "uuid": uuid_val,
                    "document_id": doc_id,
                    **props,  # Include all properties
                }

                return [{"n": created_documents[doc_id]}]

        # Handle document retrieval
        elif "MATCH" in query and "document_id" in parameters:
            doc_id = parameters["document_id"]
            if doc_id in created_documents:
                return [{"d": created_documents[doc_id]}]
            else:
                return []

        # Handle document updates
        elif "SET" in query and "document_id" in parameters:
            doc_id = parameters["document_id"]
            if doc_id in created_documents:
                # Update the stored document with new properties
                for key, value in parameters.items():
                    if key != "document_id":
                        created_documents[doc_id][key] = value
                return [{"d": created_documents[doc_id]}]
            else:
                return []

        # Default response
        return [
            {
                "d": {
                    "id": "test_node_id",
                    "document_id": "test_doc_id",
                    "title": "Test Document",
                    "content": "test content",
                }
            }
        ]

    # Create a wrapper that can handle both sync and async calls
    def sync_execute_query(query: str, parameters: dict | None = None, **kwargs):
        """Synchronous wrapper for mock_execute_query."""
        return mock_execute_query(query, parameters, **kwargs)

    mock_manager.execute_query = sync_execute_query  # Synchronous for asyncio.to_thread
    mock_manager.execute_read_query.side_effect = mock_execute_query
    mock_manager.execute_write_query.side_effect = mock_execute_query
    mock_manager.execute_write_transaction.side_effect = mock_execute_query
    mock_manager.execute_read_transaction.side_effect = mock_execute_query
    mock_manager.health_check.return_value = {"status": "healthy"}
    mock_manager.test_connection.return_value = True
    mock_manager.is_connected = True

    # Mock the driver property and _driver attribute
    # The Neo4jTransactionManager expects a synchronous driver interface
    mock_driver = Mock()  # Use Mock instead of AsyncMock for synchronous interface

    # Create a mock transaction that has the expected synchronous methods
    mock_transaction = Mock()
    mock_transaction.run = Mock(
        side_effect=lambda query, **params: mock_execute_query(query, params)
    )
    mock_transaction.commit = Mock()
    mock_transaction.rollback = Mock()
    mock_transaction.close = Mock()

    # Mock session-based transactions (synchronous)
    mock_session = Mock()
    mock_session.begin_transaction = Mock(return_value=mock_transaction)
    mock_session.run = Mock(side_effect=lambda query, **params: [])
    mock_session.close = Mock()

    # Mock the driver.session() method to return the mock session
    mock_driver.session = Mock(return_value=mock_session)

    mock_manager.driver = mock_driver
    mock_manager._driver = mock_driver

    yield mock_manager
