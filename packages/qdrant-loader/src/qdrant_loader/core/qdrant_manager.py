import asyncio
import os
from dataclasses import dataclass
from typing import Any, cast
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

_TRUE_VALUES = {"1", "true", "t", "yes", "y", "on"}
_FALSE_VALUES = {"0", "false", "f", "no", "n", "off"}


@dataclass
class SparseRuntimeConfig:
    enabled: bool = True
    model: str = "bm25"
    dense_vector_name: str = "dense"
    sparse_vector_name: str = "sparse"
    auto_fallback: bool = True


@dataclass
class CollectionVectorCapabilities:
    has_named_dense: bool = False
    has_sparse: bool = False


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
        self.sparse_runtime = self._resolve_sparse_runtime_config()
        self._sparse_encoder: Any | None = None
        self._collection_vector_capabilities: CollectionVectorCapabilities | None = None
        self._sparse_fallback_warning_emitted = False
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

    @staticmethod
    def _parse_bool(value: object, default: bool) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        normalized = str(value).strip().lower()
        if normalized in _TRUE_VALUES:
            return True
        if normalized in _FALSE_VALUES:
            return False
        return default

    def _resolve_sparse_runtime_config(self) -> SparseRuntimeConfig:
        cfg = SparseRuntimeConfig()
        try:
            llm = getattr(get_global_config(), "llm", None)
            if isinstance(llm, dict):
                sparse_cfg = {}
                if isinstance(llm.get("sparse"), dict):
                    sparse_cfg.update(llm["sparse"])
                retrieval_cfg = llm.get("retrieval")
                if isinstance(retrieval_cfg, dict) and isinstance(
                    retrieval_cfg.get("sparse"), dict
                ):
                    sparse_cfg.update(retrieval_cfg["sparse"])

                cfg.enabled = self._parse_bool(sparse_cfg.get("enabled"), cfg.enabled)
                cfg.model = str(sparse_cfg.get("model") or cfg.model)
                cfg.dense_vector_name = str(
                    sparse_cfg.get("dense_vector_name") or cfg.dense_vector_name
                )
                cfg.sparse_vector_name = str(
                    sparse_cfg.get("sparse_vector_name") or cfg.sparse_vector_name
                )
                cfg.auto_fallback = self._parse_bool(
                    sparse_cfg.get("auto_fallback"), cfg.auto_fallback
                )
        except Exception:
            pass

        cfg.enabled = self._parse_bool(os.getenv("LLM_SPARSE_ENABLED"), cfg.enabled)
        cfg.model = str(os.getenv("LLM_SPARSE_MODEL") or cfg.model)
        cfg.dense_vector_name = str(
            os.getenv("LLM_DENSE_VECTOR_NAME") or cfg.dense_vector_name
        )
        cfg.sparse_vector_name = str(
            os.getenv("LLM_SPARSE_VECTOR_NAME") or cfg.sparse_vector_name
        )
        cfg.auto_fallback = self._parse_bool(
            os.getenv("LLM_SPARSE_AUTO_FALLBACK"), cfg.auto_fallback
        )
        return cfg

    @staticmethod
    def _model_to_dict(value: object) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        if hasattr(value, "model_dump"):
            try:
                dumped = value.model_dump()  # type: ignore[call-arg]
                if isinstance(dumped, dict):
                    return dumped
            except Exception:
                return {}
        if hasattr(value, "dict"):
            try:
                dumped = value.dict()  # type: ignore[call-arg]
                if isinstance(dumped, dict):
                    return dumped
            except Exception:
                return {}
        return {}

    def _get_collection_vector_capabilities(self) -> CollectionVectorCapabilities:
        if self._collection_vector_capabilities is not None:
            return self._collection_vector_capabilities

        default_caps = CollectionVectorCapabilities()
        try:
            client = self._ensure_client_connected()
            info = client.get_collection(collection_name=self.collection_name)
            params = getattr(getattr(info, "config", None), "params", None)
            vectors = getattr(params, "vectors", None)
            sparse_vectors = getattr(params, "sparse_vectors", None)

            has_named_dense = False
            if isinstance(vectors, dict):
                has_named_dense = self.sparse_runtime.dense_vector_name in vectors
            else:
                vectors_dict = self._model_to_dict(vectors)
                has_named_dense = self.sparse_runtime.dense_vector_name in vectors_dict

            sparse_dict = self._model_to_dict(sparse_vectors)
            has_sparse = self.sparse_runtime.sparse_vector_name in sparse_dict

            self._collection_vector_capabilities = CollectionVectorCapabilities(
                has_named_dense=has_named_dense, has_sparse=has_sparse
            )
            return self._collection_vector_capabilities
        except Exception:
            self._collection_vector_capabilities = default_caps
            return default_caps

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

    def _get_sparse_encoder(self):
        if self._sparse_encoder is not None:
            return self._sparse_encoder
        from qdrant_loader_core.sparse import BM25SparseEncoder

        self._sparse_encoder = BM25SparseEncoder(model=self.sparse_runtime.model)
        return self._sparse_encoder

    def build_point_vector(self, dense_embedding: list[float], text: str) -> object:
        """Build point vector payload for upsert (dense-only or dense+sparse)."""
        if self._sparse_upsert_enabled():
            try:
                encoder = self._get_sparse_encoder()
                sparse = encoder.encode_document(text)
                if sparse.is_empty():
                    return {self.sparse_runtime.dense_vector_name: dense_embedding}
                return {
                    self.sparse_runtime.dense_vector_name: dense_embedding,
                    self.sparse_runtime.sparse_vector_name: models.SparseVector(
                        indices=sparse.indices, values=sparse.values
                    ),
                }
            except Exception as e:
                self.logger.warning(
                    "Failed to generate sparse vectors; falling back to dense-only upsert",
                    error=str(e),
                )
                if self._dense_query_using() is not None:
                    return {self.sparse_runtime.dense_vector_name: dense_embedding}
                return dense_embedding

        if self._dense_query_using() is not None:
            return {self.sparse_runtime.dense_vector_name: dense_embedding}
        return dense_embedding

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

            created_with_sparse = False
            if self.sparse_runtime.enabled:
                try:
                    client.create_collection(
                        collection_name=self.collection_name,
                        vectors_config={
                            self.sparse_runtime.dense_vector_name: VectorParams(
                                size=vector_size, distance=Distance.COSINE
                            )
                        },
                        sparse_vectors_config={
                            self.sparse_runtime.sparse_vector_name: (
                                models.SparseVectorParams()
                            )
                        },
                    )
                    created_with_sparse = True
                    self.logger.info(
                        "Created collection with dense+sparse vector schema",
                        collection=self.collection_name,
                        dense_vector_name=self.sparse_runtime.dense_vector_name,
                        sparse_vector_name=self.sparse_runtime.sparse_vector_name,
                        sparse_model=self.sparse_runtime.model,
                    )
                except Exception as sparse_error:
                    if not self.sparse_runtime.auto_fallback:
                        raise
                    self.logger.warning(
                        "Sparse collection creation failed; falling back to dense-only schema",
                        collection=self.collection_name,
                        error=str(sparse_error),
                    )

            if not created_with_sparse:
                # Create collection with basic dense-only configuration
                client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=vector_size, distance=Distance.COSINE
                    ),
                )

            self._collection_vector_capabilities = CollectionVectorCapabilities(
                has_named_dense=created_with_sparse,
                has_sparse=created_with_sparse,
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
