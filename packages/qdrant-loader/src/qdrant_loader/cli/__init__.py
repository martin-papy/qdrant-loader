"""
Command Line Interface package for QDrant Loader.
"""

from qdrant_loader.config import get_settings
from qdrant_loader.core.async_ingestion_pipeline import AsyncIngestionPipeline
from qdrant_loader.core.init_collection import init_collection
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)

__all__ = ["AsyncIngestionPipeline", "init_collection", "get_settings", "logger"]
