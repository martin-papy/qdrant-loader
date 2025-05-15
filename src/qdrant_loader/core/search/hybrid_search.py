"""Hybrid search implementation combining vector and keyword search."""

import logging
from typing import List, Dict, Any, Optional, cast
from dataclasses import dataclass
from rank_bm25 import BM25Okapi
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_loader.core.embedding.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Container for search results."""
    id: str
    score: float
    content: str
    metadata: Dict[str, Any]
    vector_score: float
    keyword_score: float

class HybridSearchService:
    """Service for hybrid search combining vector and keyword search."""

    def __init__(
        self,
        qdrant_client: QdrantClient,
        embedding_service: EmbeddingService,
        collection_name: str,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
        min_score: float = 0.3
    ):
        """Initialize the hybrid search service.

        Args:
            qdrant_client: Qdrant client instance
            embedding_service: Service for generating embeddings
            collection_name: Name of the Qdrant collection
            vector_weight: Weight for vector search scores (0-1)
            keyword_weight: Weight for keyword search scores (0-1)
            min_score: Minimum combined score threshold
        """
        self.qdrant_client = qdrant_client
        self.embedding_service = embedding_service
        self.collection_name = collection_name
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
        self.min_score = min_score
        self.logger = logging.getLogger(__name__)

    async def search(
        self,
        query: str,
        limit: int = 5,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Perform hybrid search combining vector and keyword search.

        Args:
            query: Search query
            limit: Maximum number of results to return
            filter_conditions: Optional filter conditions for Qdrant

        Returns:
            List of SearchResult objects
        """
        self.logger.debug(
            "Starting hybrid search",
            extra={
                "query": query,
                "limit": limit,
                "filter_conditions": filter_conditions
            }
        )

        try:
            # Get vector search results
            vector_results = await self._vector_search(query, limit * 2, filter_conditions)
            
            # Get keyword search results
            keyword_results = await self._keyword_search(query, limit * 2, filter_conditions)
            
            # Combine and rerank results
            combined_results = self._combine_results(vector_results, keyword_results, limit)
            
            self.logger.debug(
                "Completed hybrid search",
                extra={
                    "query": query,
                    "result_count": len(combined_results)
                }
            )
            
            return combined_results

        except Exception as e:
            self.logger.error(
                "Error in hybrid search",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "query": query
                }
            )
            raise

    async def _vector_search(
        self,
        query: str,
        limit: int,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Perform vector search using Qdrant.

        Args:
            query: Search query
            limit: Maximum number of results
            filter_conditions: Optional filter conditions

        Returns:
            List of search results with scores
        """
        # Generate query embedding
        query_embedding = await self.embedding_service.get_embedding(query)
        
        # Prepare search parameters
        search_params = models.SearchParams(
            hnsw_ef=128,  # Increased for better recall
            exact=False
        )
        
        # Prepare filter if conditions provided
        search_filter = None
        if filter_conditions:
            search_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key=key,
                        match=models.MatchValue(value=value)
                    )
                    for key, value in filter_conditions.items()
                ]
            )
        
        # Perform search
        results = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=limit,
            score_threshold=self.min_score,
            search_params=search_params,
            query_filter=search_filter
        )
        
        return [
            {
                "id": hit.id,
                "score": hit.score,
                "content": hit.payload.get("content", "") if hit.payload else "",
                "metadata": hit.payload.get("metadata", {}) if hit.payload else {}
            }
            for hit in results
        ]

    async def _keyword_search(
        self,
        query: str,
        limit: int,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Perform keyword search using BM25.

        Args:
            query: Search query
            limit: Maximum number of results
            filter_conditions: Optional filter conditions

        Returns:
            List of search results with scores
        """
        # Get all documents from collection
        scroll_results = self.qdrant_client.scroll(
            collection_name=self.collection_name,
            limit=10000,  # Adjust based on collection size
            with_payload=True,
            with_vectors=False
        )
        
        # Prepare documents for BM25
        documents = []
        doc_ids = []
        for point in scroll_results[0]:
            # Apply filter conditions if provided
            if filter_conditions and point.payload:
                if not all(
                    point.payload.get(key) == value
                    for key, value in filter_conditions.items()
                ):
                    continue
            
            content = point.payload.get("content", "") if point.payload else ""
            documents.append(content)
            doc_ids.append(point.id)
        
        # Create BM25 index
        tokenized_docs = [doc.split() for doc in documents]
        bm25 = BM25Okapi(tokenized_docs)
        
        # Search
        tokenized_query = query.split()
        scores = bm25.get_scores(tokenized_query)
        
        # Get top results
        top_indices = np.argsort(scores)[-limit:][::-1]
        
        return [
            {
                "id": doc_ids[idx],
                "score": float(scores[idx]),
                "content": documents[idx],
                "metadata": {}  # Add metadata if needed
            }
            for idx in top_indices
            if scores[idx] > 0
        ]

    def _combine_results(
        self,
        vector_results: List[Dict[str, Any]],
        keyword_results: List[Dict[str, Any]],
        limit: int
    ) -> List[SearchResult]:
        """Combine and rerank results from vector and keyword search.

        Args:
            vector_results: Results from vector search
            keyword_results: Results from keyword search
            limit: Maximum number of results to return

        Returns:
            List of combined and reranked SearchResult objects
        """
        # Create lookup dictionaries for quick access
        vector_dict = {r["id"]: r for r in vector_results}
        keyword_dict = {r["id"]: r for r in keyword_results}
        
        # Combine scores for all unique documents
        combined_scores = {}
        for doc_id in set(list(vector_dict.keys()) + list(keyword_dict.keys())):
            vector_score = vector_dict.get(doc_id, {}).get("score", 0)
            keyword_score = keyword_dict.get(doc_id, {}).get("score", 0)
            
            # Normalize scores to 0-1 range
            vector_score = (vector_score + 1) / 2  # Assuming cosine similarity
            keyword_score = min(keyword_score / 10, 1)  # Normalize BM25 scores
            
            # Calculate combined score
            combined_score = (
                self.vector_weight * vector_score +
                self.keyword_weight * keyword_score
            )
            
            if combined_score >= self.min_score:
                combined_scores[doc_id] = {
                    "combined_score": combined_score,
                    "vector_score": vector_score,
                    "keyword_score": keyword_score,
                    "content": vector_dict.get(doc_id, {}).get("content", ""),
                    "metadata": vector_dict.get(doc_id, {}).get("metadata", {})
                }
        
        # Sort by combined score and get top results
        sorted_results = sorted(
            combined_scores.items(),
            key=lambda x: x[1]["combined_score"],
            reverse=True
        )[:limit]
        
        # Convert to SearchResult objects
        return [
            SearchResult(
                id=doc_id,
                score=result["combined_score"],
                content=result["content"],
                metadata=result["metadata"],
                vector_score=result["vector_score"],
                keyword_score=result["keyword_score"]
            )
            for doc_id, result in sorted_results
        ] 