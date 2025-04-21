import asyncio
from typing import cast
from urllib.parse import urlparse

from qdrant_client import QdrantClient
from qdrant_client.http import models

from ..config import Settings, get_global_config, get_settings
from ..utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class QdrantConnectionError(Exception):
    """Custom exception for Qdrant connection errors."""

    def __init__(self, message: str, original_error: str | None = None, url: str | None = None):
        self.message = message
        self.original_error = original_error
        self.url = url
        super().__init__(self.message)


class QdrantManager:
    def __init__(self, settings: Settings | None = None):
        self.client: QdrantClient | None = None
        self.settings = settings or get_settings()
        if not self.settings:
            raise ValueError("Settings must be provided either through environment or constructor")
        self.collection_name = self.settings.QDRANT_COLLECTION_NAME
        self.batch_size = get_global_config().embedding.batch_size
        self.connect()

    def _is_api_key_present(self) -> bool:
        """
        Check if a valid API key is present.
        Returns True if the API key is a non-empty string that is not 'None' or 'null'.
        """
        api_key = self.settings.QDRANT_API_KEY
        if not api_key:  # Catches None, empty string, etc.
            return False
        return api_key.lower() not in ["none", "null"]

    def connect(self) -> None:
        """Establish connection to qDrant server."""
        try:
            # Ensure HTTPS is used when API key is present, but only for non-local URLs
            url = self.settings.QDRANT_URL
            api_key = self.settings.QDRANT_API_KEY if self._is_api_key_present() else None

            if api_key:
                parsed_url = urlparse(url)
                # Only force HTTPS for non-local URLs
                if parsed_url.scheme != "https" and not any(
                    host in parsed_url.netloc for host in ["localhost", "127.0.0.1"]
                ):
                    url = url.replace("http://", "https://", 1)
                    logger.warning("Forcing HTTPS connection due to API key usage")

            try:
                self.client = QdrantClient(
                    url=url,
                    api_key=api_key,
                    timeout=60,  # 60 seconds timeout
                )
                # Note: The version check warning is expected when connecting to Qdrant Cloud instances.
                # This occurs because the version check endpoint might not be accessible due to security restrictions.
                # The warning can be safely ignored as it doesn't affect functionality.
                logger.info("Successfully connected to qDrant")
            except Exception as e:
                error_msg = str(e)
                if "Connection refused" in error_msg:
                    raise QdrantConnectionError(
                        "Failed to connect to Qdrant: Connection refused. Please check if the Qdrant server is running and accessible at the specified URL.",
                        original_error=error_msg,
                        url=url,
                    ) from e
                elif "Invalid API key" in error_msg:
                    raise QdrantConnectionError(
                        "Failed to connect to Qdrant: Invalid API key. Please check your QDRANT_API_KEY environment variable.",
                        original_error=error_msg,
                    ) from e
                elif "timeout" in error_msg.lower():
                    raise QdrantConnectionError(
                        "Failed to connect to Qdrant: Connection timeout. Please check if the Qdrant server is running and accessible at the specified URL.",
                        original_error=error_msg,
                        url=url,
                    ) from e
                else:
                    raise QdrantConnectionError(
                        "Failed to connect to Qdrant: Unexpected error. Please check your configuration and ensure the Qdrant server is running.",
                        original_error=error_msg,
                        url=url,
                    ) from e
        except QdrantConnectionError:
            raise
        except Exception as e:
            raise QdrantConnectionError(
                "Failed to connect to qDrant: Unexpected error", original_error=str(e), url=url
            ) from e

    def _ensure_client_connected(self) -> QdrantClient:
        """Ensure the client is connected before performing operations."""
        if self.client is None:
            raise QdrantConnectionError(
                "Qdrant client is not connected. Please call connect() first."
            )
        return cast(QdrantClient, self.client)

    def create_collection(self) -> None:
        """Create a new collection if it doesn't exist."""
        try:
            client = self._ensure_client_connected()
            # Check if collection already exists
            collections = client.get_collections()
            if any(c.name == self.collection_name for c in collections.collections):
                logger.info(f"Collection {self.collection_name} already exists")
                return

            # Get vector size from configuration
            vector_size = self.settings.global_config.embedding.vector_size
            if not vector_size:
                logger.warning("No vector_size specified in config, defaulting to 1536")
                vector_size = 1536

            # Create collection with basic configuration
            client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size, distance=models.Distance.COSINE
                ),
            )
            logger.info(
                f"Collection {self.collection_name} created successfully with vector size {vector_size}"
            )
        except Exception as e:
            logger.error("Failed to create collection", error=str(e))
            raise

    async def upsert_points(self, points: list[models.PointStruct]) -> None:
        """Upsert points to the collection."""
        try:
            client = self._ensure_client_connected()
            await asyncio.to_thread(
                client.upsert,
                collection_name=self.collection_name,
                points=points,
            )
            logger.debug(f"Successfully upserted {len(points)} points")
        except Exception as e:
            logger.error("Failed to upsert points", error=str(e))
            raise

    def search(self, query_vector: list[float], limit: int = 5) -> list[models.ScoredPoint]:
        """Search for similar vectors in the collection."""
        try:
            client = self._ensure_client_connected()
            search_result = client.search(
                collection_name=self.collection_name, query_vector=query_vector, limit=limit
            )
            return search_result
        except Exception as e:
            logger.error("Failed to search collection", error=str(e))
            raise

    def delete_collection(self) -> None:
        """Delete the collection."""
        try:
            client = self._ensure_client_connected()
            client.delete_collection(collection_name=self.collection_name)
            logger.info("Deleted collection", collection=self.collection_name)
        except Exception as e:
            logger.error("Failed to delete collection", error=str(e))
            raise

    async def delete_points_by_document_id(self, document_id: str) -> None:
        """Delete all points associated with a document ID.

        Args:
            document_id: The ID of the document whose points should be deleted
        """
        try:
            client = self._ensure_client_connected()
            await asyncio.to_thread(
                client.delete,
                collection_name=self.collection_name,
                points_selector=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id),
                        )
                    ]
                ),
            )
            logger.info(f"Successfully deleted points for document {document_id}")
        except Exception as e:
            logger.error(f"Failed to delete points for document {document_id}", error=str(e))
            raise
