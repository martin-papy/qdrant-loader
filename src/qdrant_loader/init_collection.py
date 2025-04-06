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
        
        # Create collection with 1536 dimensions (matching OpenAI's text-embedding-3-small)
        manager.create_collection(vector_size=1536)
        
        logger.info("Successfully initialized qDrant collection")
    except Exception as e:
        logger.error("Failed to initialize collection", error=str(e))
        raise

if __name__ == "__main__":
    init_collection() 