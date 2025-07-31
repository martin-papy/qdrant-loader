"""Vector search service for hybrid search."""

from typing import Any

from openai import AsyncOpenAI
from qdrant_client import QdrantClient
from qdrant_client.http import models

from ...utils.logging import LoggingConfig


class VectorSearchService:
    """Handles vector search operations using Qdrant."""

    def __init__(
        self,
        qdrant_client: QdrantClient,
        openai_client: AsyncOpenAI,
        collection_name: str,
        min_score: float = 0.3,
        dense_vector_name: str = "dense",
        sparse_vector_name: str = "sparse",
        alpha: float = 0.5,
    ):
        """Initialize the vector search service.
        
        Args:
            qdrant_client: Qdrant client instance
            openai_client: OpenAI client instance
            collection_name: Name of the Qdrant collection
            min_score: Minimum score threshold
            dense_vector_name: Name of the dense vector field
            sparse_vector_name: Name of the sparse vector field
            alpha: Weight for dense search (1-alpha for sparse search)
        """
        self.qdrant_client = qdrant_client
        self.openai_client = openai_client
        self.collection_name = collection_name
        self.min_score = min_score
        self.dense_vector_name = dense_vector_name
        self.sparse_vector_name = sparse_vector_name
        self.alpha = alpha
        self.logger = LoggingConfig.get_logger(__name__)

    async def get_embedding(self, text: str) -> list[float]:
        """Get embedding for text using OpenAI.
        
        Args:
            text: Text to get embedding for
            
        Returns:
            List of embedding values
            
        Raises:
            Exception: If embedding generation fails
        """
        try:
            response = await self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            self.logger.error("Failed to get embedding", error=str(e))
            raise

    async def vector_search(
        self, 
        query: str, 
        limit: int, 
        project_ids: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Perform vector search using Qdrant.
        
        Args:
            query: Search query
            limit: Maximum number of results
            project_ids: Optional project ID filters
            
        Returns:
            List of search results with scores, text, metadata, and source_type
        """
        query_embedding = await self.get_embedding(query)

        search_params = models.SearchParams(hnsw_ef=128, exact=False)

        results = await self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=limit,
            score_threshold=self.min_score,
            search_params=search_params,
            query_filter=self._build_filter(project_ids),
            with_payload=True,  # 🔧 CRITICAL: Explicitly request payload data
        )

        extracted_results = []
        for hit in results:
            extracted = {
                "score": hit.score,
                "text": hit.payload.get("content", "") if hit.payload else "",
                "metadata": hit.payload.get("metadata", {}) if hit.payload else {},
                "source_type": hit.payload.get("source_type", "unknown") if hit.payload else "unknown",
                # Extract fields directly from Qdrant payload
                "title": hit.payload.get("title", "") if hit.payload else "",
                "url": hit.payload.get("url", "") if hit.payload else "",
                "document_id": hit.payload.get("document_id", "") if hit.payload else "",
                "source": hit.payload.get("source", "") if hit.payload else "",
                "created_at": hit.payload.get("created_at", "") if hit.payload else "",
                "updated_at": hit.payload.get("updated_at", "") if hit.payload else "",
            }
            
            extracted_results.append(extracted)
            
        return extracted_results

    def _build_filter(
        self, project_ids: list[str] | None = None
    ) -> models.Filter | None:
        """Build a Qdrant filter based on project IDs.
        
        Args:
            project_ids: Optional list of project IDs to filter by
            
        Returns:
            Qdrant filter object or None if no filtering needed
        """
        if not project_ids:
            return None

        return models.Filter(
            must=[
                models.FieldCondition(
                    key="project_id", match=models.MatchAny(any=project_ids)
                )
            ]
        )