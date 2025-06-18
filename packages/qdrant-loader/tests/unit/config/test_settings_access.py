"""
Unit tests for the settings_access module.
"""

import pytest
from unittest.mock import MagicMock, patch

from qdrant_loader.config.settings_access import (
    ConfigAccessor,
    NetworkLimits,
    TextProcessingLimits,
    ChunkingLimits,
    EntityExtractionLimits,
    PerformanceLimits,
    PipelineLimits,
    SearchLimits,
    CacheLimits,
    WorkerLimits,
    ServerLimits,
    get_chunk_size,
    get_chunk_overlap,
    get_qdrant_url,
    get_qdrant_collection_name,
    get_openai_api_key,
    get_neo4j_uri,
    get_neo4j_user,
    get_neo4j_password,
    get_neo4j_database,
)


@patch("qdrant_loader.config.settings_access.get_settings")
def test_config_accessor_lazy_loading(mock_get_settings):
    """Test that ConfigAccessor lazy-loads settings and calls get_settings only once."""
    mock_get_settings.return_value = "fake_settings"
    accessor = ConfigAccessor()
    _ = accessor.settings
    _ = accessor.settings
    mock_get_settings.assert_called_once()
    assert accessor._settings == "fake_settings"


# Tests for Limit Classes
def test_network_limits():
    assert NetworkLimits.max_file_size() == 52428800
    assert NetworkLimits.request_timeout() == 30.0
    assert NetworkLimits.http_timeout() == 60.0
    assert NetworkLimits.retry_attempts() == 3
    assert NetworkLimits.retry_delay() == 1.0


def test_text_processing_limits():
    assert TextProcessingLimits.max_text_length_for_spacy() == 100_000
    assert TextProcessingLimits.max_entities_to_extract() == 50
    assert TextProcessingLimits.max_pos_tags_to_extract() == 200


def test_chunking_limits():
    assert ChunkingLimits.max_chunks_to_process() == 1000
    assert ChunkingLimits.min_section_size() == 500
    assert ChunkingLimits.max_chunks_per_section() == 100
    assert ChunkingLimits.max_chunks_per_document() == 500
    assert ChunkingLimits.max_elements_to_process() == 800
    assert ChunkingLimits.chunk_size_threshold() == 40_000
    assert ChunkingLimits.max_element_size() == 20_000
    assert ChunkingLimits.max_html_size_for_parsing() == 500_000
    assert ChunkingLimits.max_sections_to_process() == 200
    assert ChunkingLimits.max_chunk_size_for_nlp() == 20_000
    assert ChunkingLimits.simple_parsing_threshold() == 100_000
    assert ChunkingLimits.max_objects_to_process() == 200
    assert ChunkingLimits.max_array_items_to_process() == 50
    assert ChunkingLimits.max_object_keys_to_process() == 100
    assert ChunkingLimits.simple_chunking_threshold() == 500_000


def test_entity_extraction_limits():
    assert EntityExtractionLimits.batch_size() == 10
    assert EntityExtractionLimits.cache_ttl() == 3600
    assert EntityExtractionLimits.max_text_length() == 10000
    assert EntityExtractionLimits.confidence_threshold() == 0.5
    assert EntityExtractionLimits.max_entities() == 50
    assert EntityExtractionLimits.retry_delay() == 1.0
    assert EntityExtractionLimits.queue_max_size() == 1000
    assert EntityExtractionLimits.progress_callback_interval() == 1.0
    assert EntityExtractionLimits.task_timeout() == 300.0


def test_performance_limits():
    assert PerformanceLimits.cpu_threshold() == 80.0
    assert PerformanceLimits.memory_threshold() == 80.0
    assert PerformanceLimits.monitoring_interval() == 5.0
    assert PerformanceLimits.base_timeout() == 10.0
    assert PerformanceLimits.vector_size() == 1536


def test_pipeline_limits():
    assert PipelineLimits.max_concurrent_files() == 10
    assert PipelineLimits.max_workers() == 4
    assert PipelineLimits.batch_size() == 100
    assert PipelineLimits.processing_timeout() == 300.0
    assert PipelineLimits.file_timeout() == 300.0
    assert PipelineLimits.queue_max_size() == 1000
    assert PipelineLimits.progress_interval() == 5.0


def test_search_limits():
    assert SearchLimits.max_results() == 100
    assert SearchLimits.default_limit() == 10
    assert SearchLimits.similarity_threshold() == 0.7
    assert SearchLimits.max_query_length() == 512
    assert SearchLimits.search_timeout() == 30.0


def test_cache_limits():
    assert CacheLimits.embedding_cache_ttl() == 3600
    assert CacheLimits.metadata_cache_ttl() == 3600
    assert CacheLimits.search_cache_ttl() == 600
    assert CacheLimits.max_cache_size() == 10000
    assert CacheLimits.cleanup_interval() == 3600


def test_worker_limits():
    assert WorkerLimits.min_workers() == 1
    assert WorkerLimits.max_workers() == 10
    assert WorkerLimits.max_tasks_per_worker() == 100
    assert WorkerLimits.worker_timeout() == 300.0
    assert WorkerLimits.task_queue_size() == 1000
    assert WorkerLimits.health_check_interval() == 30.0


def test_server_limits():
    assert ServerLimits.mcp_server_port() == 8000
    assert ServerLimits.prometheus_port() == 9090
    assert ServerLimits.external_api_base_url() == "http://localhost:8000"


# Tests for Getter Functions
@pytest.fixture
def mock_config_accessor():
    """Mock the global 'config' object in settings_access."""
    with patch("qdrant_loader.config.settings_access.config") as mock_config:
        yield mock_config


def test_get_chunk_size(mock_config_accessor):
    mock_config_accessor.global_config.chunking.chunk_size = 999
    assert get_chunk_size() == 999


def test_get_chunk_overlap(mock_config_accessor):
    mock_config_accessor.global_config.chunking.chunk_overlap = 111
    assert get_chunk_overlap() == 111


def test_get_qdrant_url(mock_config_accessor):
    mock_config_accessor.settings.qdrant_url = "http://fake.qdrant"
    assert get_qdrant_url() == "http://fake.qdrant"


def test_get_qdrant_collection_name(mock_config_accessor):
    mock_config_accessor.settings.qdrant_collection_name = "fake-collection"
    assert get_qdrant_collection_name() == "fake-collection"


def test_get_openai_api_key(mock_config_accessor):
    mock_config_accessor.settings.openai_api_key = "fake-api-key"
    assert get_openai_api_key() == "fake-api-key"


def test_get_neo4j_uri(mock_config_accessor):
    mock_config_accessor.settings.neo4j_uri = "bolt://fake:7687"
    assert get_neo4j_uri() == "bolt://fake:7687"


def test_get_neo4j_user(mock_config_accessor):
    mock_config_accessor.settings.neo4j_user = "fake_user"
    assert get_neo4j_user() == "fake_user"


def test_get_neo4j_password(mock_config_accessor):
    mock_config_accessor.settings.neo4j_password = "fake_password"
    assert get_neo4j_password() == "fake_password"


def test_get_neo4j_database(mock_config_accessor):
    mock_config_accessor.settings.neo4j_database = "fake_db"
    assert get_neo4j_database() == "fake_db"
