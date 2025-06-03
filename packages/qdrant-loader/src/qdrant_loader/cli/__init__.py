"""
Command Line Interface package for QDrant Loader.
"""


# Lazy imports to avoid slow package loading
def __getattr__(name):
    """Lazy import heavy modules only when accessed."""
    if name == "get_settings":
        from qdrant_loader.config import get_settings

        return get_settings
    elif name == "AsyncIngestionPipeline":
        from qdrant_loader.core.async_ingestion_pipeline import AsyncIngestionPipeline

        return AsyncIngestionPipeline
    elif name == "init_collection":
        from qdrant_loader.core.init_collection import init_collection

        return init_collection
    elif name == "logger":
        from qdrant_loader.utils.logging import LoggingConfig

        return LoggingConfig.get_logger(__name__)
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = ["AsyncIngestionPipeline", "init_collection", "get_settings", "logger"]
