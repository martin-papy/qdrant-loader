import asyncio

from qdrant_loader.config import get_settings
from qdrant_loader.core.qdrant_manager import QdrantManager
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger()


async def init_collection(settings=None, force=False):
    """Initialize the qDrant collection with proper configuration.

    Args:
        settings: Optional settings object. If not provided, will be loaded from environment.
        force: If True, will recreate the collection even if it exists.
    """
    try:
        if not settings:
            settings = get_settings()
        if not settings:
            raise ValueError(
                "Settings not available. Please check your environment variables."
            )

        # Initialize the manager
        manager = QdrantManager(settings=settings)

        if force:
            try:
                manager.delete_collection()
                logger.debug(
                    "Recreating collection",
                    collection=settings.qdrant_collection_name,
                )
            except Exception:
                # Ignore errors if collection doesn't exist
                pass
        else:
            logger.debug(
                "Initializing collection",
                collection=settings.qdrant_collection_name,
            )

        # Create collection (vector size is hardcoded to 1536 in QdrantManager)
        manager.create_collection()

        logger.debug("Collection initialization completed")
        return True
    except Exception as e:
        logger.error("Failed to initialize collection", error=str(e))
        raise


if __name__ == "__main__":
    asyncio.run(init_collection())
