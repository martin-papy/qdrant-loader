"""
Command Line Interface package for QDrant Loader.
"""

from qdrant_loader.core.ingestion_pipeline import IngestionPipeline
from qdrant_loader.core.init_collection import init_collection
from qdrant_loader.config import get_settings
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)

__all__ = ["IngestionPipeline", "init_collection", "get_settings", "logger"]
