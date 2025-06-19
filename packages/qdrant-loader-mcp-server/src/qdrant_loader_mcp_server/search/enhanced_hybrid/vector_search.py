"""Vector search module for the enhanced hybrid search engine."""

from openai import AsyncOpenAI
from qdrant_client import QdrantClient
from qdrant_client.http import models

from ...utils.logging import LoggingConfig
from .models import EnhancedSearchResult


class VectorSearchModule:
    """Enhanced vector search module using QDrant."""

    def __init__(
        self,
        qdrant_client: QdrantClient,
        openai_client: AsyncOpenAI,
        collection_name: str,
    ):
        """Initialize vector search module.

        Args:
            qdrant_client: QDrant client instance
            openai_client: OpenAI client instance
            collection_name: Name of the Qdrant collection
        """
        self.qdrant_client = qdrant_client
        self.openai_client = openai_client
        self.collection_name = collection_name
        self.logger = LoggingConfig.get_logger(__name__)

    async def search(
        self,
        query: str,
        limit: int,
        min_score: float = 0.3,
        project_ids: list[str] | None = None,
        **kwargs,
    ) -> list[EnhancedSearchResult]:
        """Perform vector search using QDrant.

        Args:
            query: Search query text
            limit: Maximum number of results
            min_score: Minimum similarity score threshold
            project_ids: Optional project ID filter
            **kwargs: Additional search parameters

        Returns:
            List of search results with vector scores
        """
        try:
            # Get query embedding
            query_embedding = await self._get_embedding(query)

            # Build filter for project IDs
            search_filter = self._build_filter(project_ids) if project_ids else None

            # Perform vector search
            search_params = models.SearchParams(hnsw_ef=128, exact=False)

            results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=min_score,
                search_params=search_params,
                query_filter=search_filter,
            )

            # Convert to EnhancedSearchResult objects
            search_results = []
            for result in results:
                if result.score >= min_score:
                    payload = result.payload or {}
                    metadata = payload.get("metadata", {})

                    search_result = EnhancedSearchResult(
                        id=str(result.id),
                        content=payload.get("content", ""),
                        title=metadata.get("title", ""),
                        source_type=payload.get("source_type", "unknown"),
                        combined_score=result.score,
                        vector_score=result.score,
                        vector_distance=1.0
                        - result.score,  # Convert similarity to distance
                        metadata=metadata,
                        debug_info={
                            "search_type": "vector",
                            "qdrant_id": str(result.id),
                        },
                    )
                    search_results.append(search_result)

            self.logger.debug(f"Vector search returned {len(search_results)} results")
            return search_results

        except Exception as e:
            self.logger.error(f"Vector search failed: {e}")
            raise

    async def _get_embedding(self, text: str) -> list[float]:
        """Get embedding for text using OpenAI."""
        try:
            response = await self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            self.logger.error(f"Failed to get embedding: {e}")
            raise

    def _build_filter(self, project_ids: list[str]) -> models.Filter:
        """Build filter for project IDs."""
        return models.Filter(
            must=[
                models.FieldCondition(
                    key="project_id", match=models.MatchAny(any=project_ids)
                )
            ]
        )
