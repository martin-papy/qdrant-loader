from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse
import structlog
from typing import Optional, List
from .config import Settings, get_settings, get_global_config

logger = structlog.get_logger()

class QdrantManager:
    def __init__(self, settings: Optional[Settings] = None):
        self.client = None
        self.settings = settings or get_settings()
        if not self.settings:
            raise ValueError("Settings must be provided either through environment or constructor")
        self.collection_name = self.settings.QDRANT_COLLECTION_NAME
        self.batch_size = get_global_config().embedding.batch_size
        self.connect()

    def connect(self) -> None:
        """Establish connection to qDrant server."""
        try:
            self.client = QdrantClient(
                url=self.settings.QDRANT_URL,
                api_key=self.settings.QDRANT_API_KEY,
                timeout=60  # 60 seconds timeout
            )
            logger.info("Successfully connected to qDrant")
        except Exception as e:
            logger.error("Failed to connect to qDrant", error=str(e))
            raise

    def create_collection(self, vector_size: int = 1536) -> None:
        """Create a new collection if it doesn't exist."""
        try:
            collections = self.client.get_collections().collections
            collection_names = [collection.name for collection in collections]
            
            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=vector_size,
                        distance=models.Distance.COSINE
                    )
                )
                logger.info("Created new collection", collection=self.collection_name)
            else:
                logger.info("Collection already exists", collection=self.collection_name)
        except UnexpectedResponse as e:
            logger.error("Failed to create collection", error=str(e))
            raise

    def upsert_points(self, points: List[models.PointStruct]) -> None:
        """Upsert points to the collection in batches."""
        try:
            total_points = len(points)
            for i in range(0, total_points, self.batch_size):
                batch = points[i:i + self.batch_size]
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch,
                    wait=True
                )
                logger.info("Upserted batch of points", 
                           batch_size=len(batch),
                           progress=f"{i + len(batch)}/{total_points}")
            logger.info("Successfully upserted all points", count=total_points)
        except Exception as e:
            logger.error("Failed to upsert points", error=str(e))
            raise

    def search(self, query_vector: List[float], limit: int = 5) -> List[models.ScoredPoint]:
        """Search for similar vectors in the collection."""
        try:
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit
            )
            return search_result
        except Exception as e:
            logger.error("Failed to search collection", error=str(e))
            raise

    def delete_collection(self) -> None:
        """Delete the collection."""
        try:
            self.client.delete_collection(collection_name=self.collection_name)
            logger.info("Deleted collection", collection=self.collection_name)
        except Exception as e:
            logger.error("Failed to delete collection", error=str(e))
            raise 