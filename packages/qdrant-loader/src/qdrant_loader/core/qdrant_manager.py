import asyncio
from typing import Any, cast
from urllib.parse import urlparse

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import (
    Distance,
    VectorParams,
)
from qdrant_loader_core.config import (
    CollectionVectorCapabilities,
    SparseRuntimeConfig,
    parse_collection_capabilities,
)
from qdrant_loader_core.sparse import get_sparse_encoder

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
        self.batch_size = self.settings.llm_settings.embeddings.batch_size
        self.sparse_runtime = self._resolve_sparse_runtime_config()
        self._collection_vector_capabilities: CollectionVectorCapabilities | None = None
        self._sparse_fallback_warning_emitted = False
        self.connect()

    @staticmethod
    def _coerce_positive_int(value: Any) -> int | None:
        if isinstance(value, bool) or value is None:
            return None
        if isinstance(value, int):
            return value if value > 0 else None
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return None
            try:
                parsed = int(text)
            except ValueError:
                return None
            return parsed if parsed > 0 else None
        return None

    def _is_api_key_present(self) -> bool:
        """
        Check if a valid API key is present.
        Returns True if the API key is a non-empty string that is not 'None' or 'null'.
        """
        api_key = self.settings.qdrant_api_key
        if not api_key:  # Catches None, empty string, etc.
            return False
        return api_key.lower() not in ["none", "null"]

    def _resolve_sparse_runtime_config(self) -> SparseRuntimeConfig:
        try:
            llm = getattr(get_global_config(), "llm", None) or {}
        except Exception as e:
            self.logger.warning(
                "Failed to read global LLM config for sparse runtime; using defaults",
                error=str(e),
                exc_info=True,
            )
            llm = {}
        global_config = {"llm": llm} if isinstance(llm, dict) else {}
        return SparseRuntimeConfig.from_global_config(global_config)

    def _get_collection_vector_capabilities(self) -> CollectionVectorCapabilities:
        if self._collection_vector_capabilities is not None:
            return self._collection_vector_capabilities

        client = self._ensure_client_connected()
        try:
            info = client.get_collection(collection_name=self.collection_name)
        except Exception as e:
            # Don't cache: a transient outage would otherwise pin every
            # subsequent upsert to dense-only payload shape even after Qdrant
            # becomes reachable again, mismatching a hybrid collection schema.
            self.logger.warning(
                "Failed to inspect Qdrant collection schema; assuming dense-only",
                collection=self.collection_name,
                error=str(e),
            )
            return CollectionVectorCapabilities()

        self._collection_vector_capabilities = parse_collection_capabilities(
            info, self.sparse_runtime
        )
        return self._collection_vector_capabilities

    def _dense_query_using(self) -> str | None:
        caps = self._get_collection_vector_capabilities()
        if caps.has_named_dense:
            return self.sparse_runtime.dense_vector_name
        return None

    def _sparse_upsert_enabled(self) -> bool:
        if not self.sparse_runtime.enabled:
            return False

        caps = self._get_collection_vector_capabilities()
        if caps.has_named_dense and caps.has_sparse:
            return True

        if not self._sparse_fallback_warning_emitted:
            self.logger.warning(
                "Sparse vectors requested but collection schema does not support them; falling back to dense-only upserts",
                collection=self.collection_name,
                dense_vector_name=self.sparse_runtime.dense_vector_name,
                sparse_vector_name=self.sparse_runtime.sparse_vector_name,
            )
            self._sparse_fallback_warning_emitted = True
        return False

    def build_point_vector(self, dense_embedding: list[float], text: str) -> object:
        """Build the point vector payload for upsert.

        Three shapes are possible depending on the live collection schema:
        - dense+sparse named dict (hybrid-ready collection),
        - dense-only named dict (legacy named-vector collection),
        - raw dense list (legacy unnamed collection).
        """
        if self._sparse_upsert_enabled():
            return self._build_hybrid_payload(dense_embedding, text)
        return self._build_dense_payload(dense_embedding)

    def _build_dense_payload(self, dense_embedding: list[float]) -> object:
        """Return dense-only payload using the named-vector shape if the collection requires it."""
        if self._dense_query_using() is not None:
            return {self.sparse_runtime.dense_vector_name: dense_embedding}
        return dense_embedding

    def _build_hybrid_payload(self, dense_embedding: list[float], text: str) -> object:
        """Return dense+sparse payload, with a dense-only fallback on encode failure."""
        try:
            sparse = get_sparse_encoder(self.sparse_runtime.model).encode_document(text)
        except Exception as e:
            self.logger.warning(
                "Failed to generate sparse vectors; falling back to dense-only upsert",
                error=str(e),
            )
            return self._build_dense_payload(dense_embedding)

        if sparse.is_empty():
            return {self.sparse_runtime.dense_vector_name: dense_embedding}
        return {
            self.sparse_runtime.dense_vector_name: dense_embedding,
            self.sparse_runtime.sparse_vector_name: models.SparseVector(
                indices=sparse.indices, values=sparse.values
            ),
        }

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

            # Use provider-agnostic LLM settings as the source of truth.
            # Legacy embedding.vector_size is consulted only when llm vector_size
            # is not set, to preserve backward compatibility.
            vector_size = self._coerce_positive_int(
                getattr(self.settings.llm_settings.embeddings, "vector_size", None)
            )

            if vector_size is None:
                self.logger.warning(
                    "No vector_size specified in config; falling back to 1024 (deprecated default). Set global.llm.embeddings.vector_size."
                )
                vector_size = 1024

            # sparse.enabled is a strict declaration. If True, the collection
            # is created with a sparse vector; failures propagate. If False,
            # dense-only. Operators on Qdrant servers that don't support sparse
            # vectors must set sparse.enabled=false explicitly.
            dense_params = VectorParams(size=vector_size, distance=Distance.COSINE)
            if self.sparse_runtime.enabled:
                client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config={
                        self.sparse_runtime.dense_vector_name: dense_params
                    },
                    sparse_vectors_config={
                        self.sparse_runtime.sparse_vector_name: models.SparseVectorParams()
                    },
                )
                self.logger.info(
                    "Created Qdrant collection with dense+sparse vectors",
                    collection=self.collection_name,
                    dense_vector_name=self.sparse_runtime.dense_vector_name,
                    sparse_vector_name=self.sparse_runtime.sparse_vector_name,
                    sparse_model=self.sparse_runtime.model,
                )
            else:
                client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=dense_params,
                )

            self._collection_vector_capabilities = CollectionVectorCapabilities(
                has_named_dense=self.sparse_runtime.enabled,
                has_sparse=self.sparse_runtime.enabled,
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
            query_kwargs: dict[str, Any] = {
                "collection_name": self.collection_name,
                "query": query_vector,
                "limit": limit,
            }
            using = self._dense_query_using()
            if using:
                query_kwargs["using"] = using
            # Use query_points API (qdrant-client 1.10+)
            query_response = client.query_points(**query_kwargs)
            return query_response.points
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

            query_kwargs: dict[str, Any] = {
                "collection_name": self.collection_name,
                "query": query_vector,
                "query_filter": project_filter,
                "limit": limit,
            }
            using = self._dense_query_using()
            if using:
                query_kwargs["using"] = using
            # Use query_points API (qdrant-client 1.10+)
            query_response = client.query_points(**query_kwargs)
            return query_response.points
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
