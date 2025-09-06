import asyncio
from typing import cast
from urllib.parse import urlparse

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import (
    Distance,
    VectorParams,
)

from ..config import Settings, get_global_config, get_settings
from ..utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class QdrantConnectionError(Exception):
    """Custom exception for Qdrant connection errors."""

    def __init__(
        self, message: str, original_error: str | None = None, url: str | None = None
    ):
        self.message = message
        self.original_error = original_error
        self.url = url
        super().__init__(self.message)


class QdrantManager:
    def __init__(self, settings: Settings | None = None):
        """Initialize the qDrant manager.

        Args:
            settings: The application settings
        """
        self.settings = settings or get_settings()
        self.client = None
        self.collection_name = self.settings.qdrant_collection_name
        self.logger = LoggingConfig.get_logger(__name__)
        self.batch_size = get_global_config().embedding.batch_size
        self.connect()

    def _is_api_key_present(self) -> bool:
        """
        Check if a valid API key is present.
        Returns True if the API key is a non-empty string that is not 'None' or 'null'.
        """
        api_key = self.settings.qdrant_api_key
        if not api_key:  # Catches None, empty string, etc.
            return False
        return api_key.lower() not in ["none", "null"]

    def connect(self) -> None:
        """Establish connection to qDrant server."""
        try:
            # Ensure HTTPS is used when API key is present, but only for non-local URLs
            url = self.settings.qdrant_url
            api_key = (
                self.settings.qdrant_api_key if self._is_api_key_present() else None
            )

            if api_key:
                parsed_url = urlparse(url)
                # Only force HTTPS for non-local URLs
                if parsed_url.scheme != "https" and not any(
                    host in parsed_url.netloc for host in ["localhost", "127.0.0.1"]
                ):
                    url = url.replace("http://", "https://", 1)
                    self.logger.warning("Forcing HTTPS connection due to API key usage")

            try:
                self.client = QdrantClient(
                    url=url,
                    api_key=api_key,
                    timeout=60,  # 60 seconds timeout
                )
                self.logger.debug("Successfully connected to qDrant")
            except Exception as e:
                raise QdrantConnectionError(
                    "Failed to connect to qDrant: Connection error",
                    original_error=str(e),
                    url=url,
                ) from e

        except Exception as e:
            raise QdrantConnectionError(
                "Failed to connect to qDrant: Unexpected error",
                original_error=str(e),
                url=url,
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
                self.logger.info(f"Collection {self.collection_name} already exists")
                return

            # Get vector size from unified LLM settings first, then legacy embedding
            vector_size: int | None = None
            try:
                global_cfg = get_global_config()
                llm_settings = getattr(global_cfg, "llm", None)
                if llm_settings is not None:
                    embeddings_cfg = getattr(llm_settings, "embeddings", None)
                    vs = (
                        getattr(embeddings_cfg, "vector_size", None)
                        if embeddings_cfg is not None
                        else None
                    )
                    if isinstance(vs, int):
                        vector_size = int(vs)
            except Exception:
                vector_size = None

            if vector_size is None:
                try:
                    legacy_vs = get_global_config().embedding.vector_size
                    if isinstance(legacy_vs, int):
                        vector_size = int(legacy_vs)
                except Exception:
                    vector_size = None

            if vector_size is None:
                self.logger.warning(
                    "No vector_size specified in config; falling back to 1536 (deprecated default). Set global.llm.embeddings.vector_size."
                )
                vector_size = 1536

            # Create collection with basic configuration
            client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )

            # Create payload indexes for optimal search performance
            indexes_to_create = [
                # Essential performance indexes
                (
                    "document_id",
                    {"type": "keyword"},
                ),  # Existing index, kept for backward compatibility
                (
                    "project_id",
                    {"type": "keyword"},
                ),  # Critical for multi-tenant filtering
                ("source_type", {"type": "keyword"}),  # Document type filtering
                ("source", {"type": "keyword"}),  # Source path filtering
                ("title", {"type": "keyword"}),  # Title-based search and filtering
                ("created_at", {"type": "keyword"}),  # Temporal filtering
                ("updated_at", {"type": "keyword"}),  # Temporal filtering
                # Secondary performance indexes
                ("is_attachment", {"type": "bool"}),  # Attachment filtering
                (
                    "parent_document_id",
                    {"type": "keyword"},
                ),  # Hierarchical relationships
                ("original_file_type", {"type": "keyword"}),  # File type filtering
                ("is_converted", {"type": "bool"}),  # Conversion status filtering
            ]

            # Create indexes with proper error handling
            created_indexes = []
            failed_indexes = []

            for field_name, field_schema in indexes_to_create:
                try:
                    client.create_payload_index(
                        collection_name=self.collection_name,
                        field_name=field_name,
                        field_schema=field_schema,  # type: ignore
                    )
                    created_indexes.append(field_name)
                    self.logger.debug(f"Created payload index for field: {field_name}")
                except Exception as e:
                    failed_indexes.append((field_name, str(e)))
                    self.logger.warning(
                        f"Failed to create index for {field_name}", error=str(e)
                    )

            # Log index creation summary
            self.logger.info(
                f"Collection {self.collection_name} created with indexes",
                created_indexes=created_indexes,
                failed_indexes=(
                    [name for name, _ in failed_indexes] if failed_indexes else None
                ),
                total_indexes_created=len(created_indexes),
            )

            if failed_indexes:
                self.logger.warning(
                    "Some indexes failed to create but collection is functional",
                    failed_details=failed_indexes,
                )
        except Exception as e:
            self.logger.error("Failed to create collection", error=str(e))
            raise

    async def upsert_points(self, points: list[models.PointStruct]) -> None:
        """Upsert points into the collection.

        Args:
            points: List of points to upsert
        """
        self.logger.debug(
            "Upserting points",
            extra={"point_count": len(points), "collection": self.collection_name},
        )

        try:
            client = self._ensure_client_connected()
            await asyncio.to_thread(
                client.upsert, collection_name=self.collection_name, points=points
            )
            self.logger.debug(
                "Successfully upserted points",
                extra={"point_count": len(points), "collection": self.collection_name},
            )
        except Exception as e:
            self.logger.error(
                "Failed to upsert points",
                extra={
                    "error": str(e),
                    "point_count": len(points),
                    "collection": self.collection_name,
                },
            )
            raise

    def search(
        self, query_vector: list[float], limit: int = 5
    ) -> list[models.ScoredPoint]:
        """Search for similar vectors in the collection."""
        try:
            client = self._ensure_client_connected()
            search_result = client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
            )
            return search_result
        except Exception as e:
            logger.error("Failed to search collection", error=str(e))
            raise

    def search_with_project_filter(
        self, query_vector: list[float], project_ids: list[str], limit: int = 5
    ) -> list[models.ScoredPoint]:
        """Search for similar vectors in the collection with project filtering.

        Args:
            query_vector: Query vector for similarity search
            project_ids: List of project IDs to filter by
            limit: Maximum number of results to return

        Returns:
            List of scored points matching the query and project filter
        """
        try:
            client = self._ensure_client_connected()

            # Build project filter
            project_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="project_id", match=models.MatchAny(any=project_ids)
                    )
                ]
            )

            search_result = client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=project_filter,
                limit=limit,
            )
            return search_result
        except Exception as e:
            logger.error(
                "Failed to search collection with project filter",
                error=str(e),
                project_ids=project_ids,
            )
            raise

    def get_project_collections(self) -> dict[str, str]:
        """Get mapping of project IDs to their collection names.

        Returns:
            Dictionary mapping project_id to collection_name
        """
        try:
            client = self._ensure_client_connected()

            # Scroll through all points to get unique project-collection mappings
            scroll_result = client.scroll(
                collection_name=self.collection_name,
                limit=10000,  # Large limit to get all unique projects
                with_payload=True,
                with_vectors=False,
            )

            project_collections = {}
            for point in scroll_result[0]:
                if point.payload:
                    project_id = point.payload.get("project_id")
                    collection_name = point.payload.get("collection_name")
                    if project_id and collection_name:
                        project_collections[project_id] = collection_name

            return project_collections
        except Exception as e:
            logger.error("Failed to get project collections", error=str(e))
            raise

    def delete_collection(self) -> None:
        """Delete the collection."""
        try:
            client = self._ensure_client_connected()
            client.delete_collection(collection_name=self.collection_name)
            logger.debug("Collection deleted", collection=self.collection_name)
        except Exception as e:
            logger.error("Failed to delete collection", error=str(e))
            raise

    async def delete_points_by_document_id(self, document_ids: list[str]) -> None:
        """Delete points from the collection by document ID.

        Args:
            document_ids: List of document IDs to delete
        """
        self.logger.debug(
            "Deleting points by document ID",
            extra={
                "document_count": len(document_ids),
                "collection": self.collection_name,
            },
        )

        try:
            client = self._ensure_client_connected()
            await asyncio.to_thread(
                client.delete,
                collection_name=self.collection_name,
                points_selector=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id", match=models.MatchAny(any=document_ids)
                        )
                    ]
                ),
            )
            self.logger.debug(
                "Successfully deleted points",
                extra={
                    "document_count": len(document_ids),
                    "collection": self.collection_name,
                },
            )
        except Exception as e:
            self.logger.error(
                "Failed to delete points",
                extra={
                    "error": str(e),
                    "document_count": len(document_ids),
                    "collection": self.collection_name,
                },
            )
            raise
