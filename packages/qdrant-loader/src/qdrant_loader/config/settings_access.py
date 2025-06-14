"""Configuration access utilities for replacing hardcoded values.

This module provides convenient access to configuration values from the
merged configuration, replacing hardcoded constants throughout the codebase.
"""

from typing import Any, Optional, TYPE_CHECKING

from . import get_settings

if TYPE_CHECKING:
    from . import Settings


class ConfigAccessor:
    """Centralized access to configuration values across all domains."""

    def __init__(self):
        """Initialize the configuration accessor."""
        self._settings: Optional["Settings"] = None

    def _ensure_loaded(self):
        """Ensure configuration is loaded."""
        if self._settings is None:
            self._settings = get_settings()

    @property
    def settings(self) -> "Settings":
        """Get the settings object."""
        self._ensure_loaded()
        return self._settings  # type: ignore

    @property
    def global_config(self):
        """Get global configuration."""
        return self.settings.global_config


# Global configuration accessor instance
config = ConfigAccessor()


# Specific value getters for commonly used hardcoded values
class NetworkLimits:
    """Network-related configuration limits."""

    @staticmethod
    def max_file_size() -> int:
        """Get maximum file size for uploads."""
        return 50 * 1024 * 1024  # 50MB default, can be made configurable

    @staticmethod
    def request_timeout() -> float:
        """Get request timeout."""
        return 30.0  # 30 seconds default

    @staticmethod
    def http_timeout() -> float:
        """Get HTTP timeout."""
        return 60.0  # 60 seconds default

    @staticmethod
    def retry_attempts() -> int:
        """Get retry attempts."""
        return 3  # 3 attempts default

    @staticmethod
    def retry_delay() -> float:
        """Get retry delay."""
        return 1.0  # 1 second default


class TextProcessingLimits:
    """Text processing configuration limits."""

    @staticmethod
    def max_text_length_for_spacy() -> int:
        """Get maximum text length for spaCy processing."""
        return 100_000  # 100k characters

    @staticmethod
    def max_entities_to_extract() -> int:
        """Get maximum entities to extract."""
        return 50

    @staticmethod
    def max_pos_tags_to_extract() -> int:
        """Get maximum POS tags to extract."""
        return 200


class ChunkingLimits:
    """Chunking strategy configuration limits."""

    @staticmethod
    def max_chunks_to_process() -> int:
        """Get maximum chunks to process."""
        return 1000

    @staticmethod
    def min_section_size() -> int:
        """Get minimum section size for markdown."""
        return 500

    @staticmethod
    def max_chunks_per_section() -> int:
        """Get maximum chunks per section."""
        return 100

    @staticmethod
    def max_chunks_per_document() -> int:
        """Get maximum chunks per document."""
        return 500

    @staticmethod
    def max_elements_to_process() -> int:
        """Get maximum code elements to process."""
        return 800

    @staticmethod
    def chunk_size_threshold() -> int:
        """Get chunk size threshold for code files."""
        return 40_000

    @staticmethod
    def max_element_size() -> int:
        """Get maximum element size."""
        return 20_000

    @staticmethod
    def max_html_size_for_parsing() -> int:
        """Get maximum HTML size for complex parsing."""
        return 500_000

    @staticmethod
    def max_sections_to_process() -> int:
        """Get maximum sections to process."""
        return 200

    @staticmethod
    def max_chunk_size_for_nlp() -> int:
        """Get maximum chunk size for NLP processing."""
        return 20_000

    @staticmethod
    def simple_parsing_threshold() -> int:
        """Get simple parsing threshold."""
        return 100_000

    @staticmethod
    def max_objects_to_process() -> int:
        """Get maximum JSON objects to process."""
        return 200

    @staticmethod
    def max_array_items_to_process() -> int:
        """Get maximum array items to process."""
        return 50

    @staticmethod
    def max_object_keys_to_process() -> int:
        """Get maximum object keys to process."""
        return 100

    @staticmethod
    def simple_chunking_threshold() -> int:
        """Get simple chunking threshold."""
        return 500_000


class EntityExtractionLimits:
    """Entity extraction configuration limits."""

    @staticmethod
    def batch_size() -> int:
        """Get entity extraction batch size."""
        return 10

    @staticmethod
    def cache_ttl() -> int:
        """Get entity extraction cache TTL."""
        return 3600  # 1 hour

    @staticmethod
    def max_text_length() -> int:
        """Get maximum text length for entity extraction."""
        return 10000

    @staticmethod
    def confidence_threshold() -> float:
        """Get confidence threshold."""
        return 0.5

    @staticmethod
    def max_entities() -> int:
        """Get maximum entities."""
        return 50

    @staticmethod
    def retry_delay() -> float:
        """Get retry delay."""
        return 1.0

    @staticmethod
    def queue_max_size() -> int:
        """Get queue maximum size."""
        return 1000

    @staticmethod
    def progress_callback_interval() -> float:
        """Get progress callback interval."""
        return 1.0

    @staticmethod
    def task_timeout() -> float:
        """Get task timeout."""
        return 300.0  # 5 minutes


class PerformanceLimits:
    """Performance monitoring configuration limits."""

    @staticmethod
    def cpu_threshold() -> float:
        """Get CPU threshold."""
        return 80.0

    @staticmethod
    def memory_threshold() -> float:
        """Get memory threshold."""
        return 80.0

    @staticmethod
    def monitoring_interval() -> float:
        """Get monitoring interval."""
        return 5.0

    @staticmethod
    def base_timeout() -> float:
        """Get base timeout."""
        return 10.0

    @staticmethod
    def vector_size() -> int:
        """Get vector size."""
        return 1536  # OpenAI embedding dimension


class PipelineLimits:
    """Pipeline configuration limits."""

    @staticmethod
    def max_concurrent_files() -> int:
        """Get maximum concurrent files."""
        return 10

    @staticmethod
    def max_workers() -> int:
        """Get maximum workers."""
        return 4

    @staticmethod
    def batch_size() -> int:
        """Get batch size."""
        return 100

    @staticmethod
    def processing_timeout() -> float:
        """Get processing timeout."""
        return 300.0  # 5 minutes

    @staticmethod
    def file_timeout() -> float:
        """Get file timeout."""
        return 60.0  # 1 minute

    @staticmethod
    def queue_max_size() -> int:
        """Get queue maximum size."""
        return 1000

    @staticmethod
    def progress_interval() -> float:
        """Get progress interval."""
        return 5.0


class SearchLimits:
    """Search configuration limits."""

    @staticmethod
    def max_results() -> int:
        """Get maximum search results."""
        return 100

    @staticmethod
    def default_limit() -> int:
        """Get default search limit."""
        return 10

    @staticmethod
    def similarity_threshold() -> float:
        """Get similarity threshold."""
        return 0.7

    @staticmethod
    def max_query_length() -> int:
        """Get maximum query length."""
        return 1000

    @staticmethod
    def search_timeout() -> float:
        """Get search timeout."""
        return 30.0


class CacheLimits:
    """Cache configuration limits."""

    @staticmethod
    def embedding_cache_ttl() -> int:
        """Get embedding cache TTL."""
        return 3600  # 1 hour

    @staticmethod
    def metadata_cache_ttl() -> int:
        """Get metadata cache TTL."""
        return 1800  # 30 minutes

    @staticmethod
    def search_cache_ttl() -> int:
        """Get search cache TTL."""
        return 300  # 5 minutes

    @staticmethod
    def max_cache_size() -> int:
        """Get maximum cache size."""
        return 1000

    @staticmethod
    def cleanup_interval() -> int:
        """Get cleanup interval."""
        return 300  # 5 minutes


class WorkerLimits:
    """Worker configuration limits."""

    @staticmethod
    def min_workers() -> int:
        """Get minimum workers."""
        return 1

    @staticmethod
    def max_workers() -> int:
        """Get maximum workers."""
        return 10

    @staticmethod
    def max_tasks_per_worker() -> int:
        """Get maximum tasks per worker."""
        return 100

    @staticmethod
    def worker_timeout() -> float:
        """Get worker timeout."""
        return 300.0  # 5 minutes

    @staticmethod
    def task_queue_size() -> int:
        """Get task queue size."""
        return 1000

    @staticmethod
    def health_check_interval() -> float:
        """Get health check interval."""
        return 30.0


class ServerLimits:
    """Server configuration limits."""

    @staticmethod
    def mcp_server_port() -> int:
        """Get MCP server port."""
        return 8000

    @staticmethod
    def prometheus_port() -> int:
        """Get Prometheus metrics port."""
        return 9090

    @staticmethod
    def external_api_base_url() -> str:
        """Get external API base URL."""
        return "http://localhost:8000"


# Convenience functions for accessing configuration values
def get_chunk_size() -> int:
    """Get the configured chunk size."""
    return config.global_config.chunking.chunk_size


def get_chunk_overlap() -> int:
    """Get the configured chunk overlap."""
    return config.global_config.chunking.chunk_overlap


def get_qdrant_url() -> str:
    """Get the QDrant URL."""
    return config.settings.qdrant_url


def get_qdrant_collection_name() -> str:
    """Get the QDrant collection name."""
    return config.settings.qdrant_collection_name


def get_openai_api_key() -> str:
    """Get the OpenAI API key."""
    return config.settings.openai_api_key


def get_neo4j_uri() -> str:
    """Get the Neo4j URI."""
    return config.settings.neo4j_uri


def get_neo4j_user() -> str:
    """Get the Neo4j user."""
    return config.settings.neo4j_user


def get_neo4j_password() -> str:
    """Get the Neo4j password."""
    return config.settings.neo4j_password


def get_neo4j_database() -> str:
    """Get the Neo4j database."""
    return config.settings.neo4j_database
