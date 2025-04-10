from .qdrant_manager import QdrantManager
from .config import get_settings
import structlog

logger = structlog.get_logger()

def init_collection():
    """Initialize the qDrant collection with proper configuration."""
    try:
        settings = get_settings()
        if not settings:
            raise ValueError("Settings not available. Please check your environment variables.")
            
        # Initialize the manager
        manager = QdrantManager(settings=settings)
        
        # Create collection (vector size is hardcoded to 1536 in QdrantManager)
        manager.create_collection()
        
        logger.info("Successfully initialized qDrant collection")
    except Exception as e:
        logger.error("Failed to initialize collection", error=str(e))
        raise

if __name__ == "__main__":
    init_collection() 