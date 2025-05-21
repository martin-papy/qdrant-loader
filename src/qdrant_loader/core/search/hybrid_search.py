"""Hybrid search implementation combining vector and keyword search."""

import logging
import re
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
        vector_weight: float = 0.6,  # Reduced from 0.7 to give more weight to keywords & metadata
        keyword_weight: float = 0.3,
        metadata_weight: float = 0.1,  # Added metadata weight
        min_score: float = 0.3
    ):
        """Initialize the hybrid search service.

        Args:
            qdrant_client: Qdrant client instance
            embedding_service: Service for generating embeddings
            collection_name: Name of the Qdrant collection
            vector_weight: Weight for vector search scores (0-1)
            keyword_weight: Weight for keyword search scores (0-1)
            metadata_weight: Weight for metadata-based scoring (0-1)
            min_score: Minimum combined score threshold
        """
        self.qdrant_client = qdrant_client
        self.embedding_service = embedding_service
        self.collection_name = collection_name
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
        self.metadata_weight = metadata_weight
        self.min_score = min_score
        self.logger = logging.getLogger(__name__)
        
        # Common query expansions for frequently used terms
        self.query_expansions = {
            "product requirements": ["PRD", "requirements document", "product specification"],
            "requirements": ["specs", "requirements document", "features"],
            "architecture": ["system design", "technical architecture"],
            "UI": ["user interface", "frontend", "design"],
            "API": ["interface", "endpoints", "REST"],
            "database": ["DB", "data storage", "persistence"],
            "security": ["auth", "authentication", "authorization"]
        }

    async def _expand_query(self, query: str) -> str:
        """Expand query with related terms for better matching.
        
        Args:
            query: Original search query
            
        Returns:
            Expanded query with relevant related terms
        """
        expanded_query = query
        lower_query = query.lower()
        
        # Look for expansion matches
        for key, expansions in self.query_expansions.items():
            if key.lower() in lower_query:
                expansion_terms = " ".join(expansions)
                expanded_query = f"{query} {expansion_terms}"
                self.logger.debug(
                    "Expanded query",
                    extra={
                        "original_query": query,
                        "expanded_query": expanded_query
                    }
                )
                break
                
        return expanded_query

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
            # Expand query with related terms
            expanded_query = await self._expand_query(query)
            
            # Get vector search results with expanded query to improve recall
            vector_results = await self._vector_search(expanded_query, limit * 3, filter_conditions)
            
            # Get keyword search results with original query for precision
            keyword_results = await self._keyword_search(query, limit * 3, filter_conditions)
            
            # Analyze query for context
            query_context = self._analyze_query(query)
            
            # Combine and rerank results with metadata awareness
            combined_results = self._combine_results(vector_results, keyword_results, query_context, limit)
            
            self.logger.debug(
                "Completed hybrid search",
                extra={
                    "query": query,
                    "expanded_query": expanded_query,
                    "result_count": len(combined_results),
                    "query_context": query_context
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

    def _analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze query to determine intent and context.
        
        Args:
            query: The search query
            
        Returns:
            Dictionary containing query analysis results
        """
        context = {
            "is_question": bool(re.search(r"\?|what|how|why|when|who|where", query.lower())),
            "is_broad": len(query.split()) < 5,
            "is_specific": len(query.split()) > 7,
            "probable_intent": "informational",  # Default intent
            "keywords": []
        }
        
        # Extract key terms for relevance
        lower_query = query.lower()
        context["keywords"] = [word.lower() for word in re.findall(r'\b\w{3,}\b', lower_query)]
        
        # Detect probable intent
        if "how to" in lower_query or "steps" in lower_query:
            context["probable_intent"] = "procedural"
        elif any(term in lower_query for term in ["requirements", "prd", "specification"]):
            context["probable_intent"] = "requirements"
        elif any(term in lower_query for term in ["architecture", "design", "structure"]):
            context["probable_intent"] = "architecture"
        
        return context

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
        metadata_list = []
        for point in scroll_results[0]:
            # Apply filter conditions if provided
            if filter_conditions and point.payload:
                if not all(
                    point.payload.get(key) == value
                    for key, value in filter_conditions.items()
                ):
                    continue
            
            content = point.payload.get("content", "") if point.payload else ""
            metadata = point.payload.get("metadata", {}) if point.payload else {}
            documents.append(content)
            doc_ids.append(point.id)
            metadata_list.append(metadata)
        
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
                "metadata": metadata_list[idx]
            }
            for idx in top_indices
            if scores[idx] > 0
        ]

    def _calculate_metadata_score(
        self, 
        metadata: Dict[str, Any],
        query_context: Dict[str, Any]
    ) -> float:
        """Calculate score adjustment based on document metadata.
        
        Args:
            metadata: Document metadata
            query_context: Query context and intent information
            
        Returns:
            Metadata score between 0.0 and 1.0
        """
        score = 0.0
        
        # Boost based on section level - higher level (lower number) sections get higher scores
        section_level = metadata.get("section_level", metadata.get("level", 100))
        if section_level < 100:  # Only if we have a valid level
            level_score = max(0, 0.2 * (1.0 - (section_level / 6)))
            score += level_score
            
        # For broad questions, boost overview/introduction sections
        if query_context.get("is_broad", False):
            section_title = metadata.get("section_title", "").lower()
            if any(term in section_title for term in ["introduction", "overview", "about", "purpose", "summary"]):
                score += 0.25
                
        # For requirements-focused queries, boost relevant sections
        if query_context.get("probable_intent") == "requirements":
            section_title = metadata.get("section_title", "").lower()
            section_path = metadata.get("section_path", "").lower()
            breadcrumb = metadata.get("breadcrumb", "").lower()
            
            # Check for requirements-related terms in section information
            if any(term in section_title for term in ["requirement", "feature", "goal", "objective"]):
                score += 0.3
            elif any(term in section_path for term in ["requirement", "feature", "goal", "objective"]):
                score += 0.2
            elif any(term in breadcrumb for term in ["requirement", "feature", "goal", "objective"]):
                score += 0.1
                
        # For top-level sections (important overviews)
        if metadata.get("is_top_level", False):
            score += 0.15
            
        # Cap at 1.0
        return min(1.0, score)

    def _combine_results(
        self,
        vector_results: List[Dict[str, Any]],
        keyword_results: List[Dict[str, Any]],
        query_context: Dict[str, Any],
        limit: int
    ) -> List[SearchResult]:
        """Combine and rerank results from vector and keyword search.

        Args:
            vector_results: Results from vector search
            keyword_results: Results from keyword search
            query_context: Context information about the query
            limit: Maximum number of results to return

        Returns:
            List of combined and reranked SearchResult objects
        """
        # Create lookup dictionaries for quick access
        vector_dict = {r["id"]: r for r in vector_results}
        keyword_dict = {r["id"]: r for r in keyword_results}
        
        # Combine scores for all unique documents
        combined_dict = {}
        
        # Process vector results
        for result in vector_results:
            doc_id = result["id"]
            if doc_id not in combined_dict:
                combined_dict[doc_id] = {
                    "id": doc_id,
                    "content": result["content"],
                    "metadata": result["metadata"],
                    "vector_score": result["score"],
                    "keyword_score": 0.0,
                    "metadata_score": 0.0
                }
        
        # Process keyword results
        for result in keyword_results:
            doc_id = result["id"]
            if doc_id in combined_dict:
                combined_dict[doc_id]["keyword_score"] = result["score"]
            else:
                combined_dict[doc_id] = {
                    "id": doc_id,
                    "content": result["content"],
                    "metadata": result["metadata"],
                    "vector_score": 0.0,
                    "keyword_score": result["score"],
                    "metadata_score": 0.0
                }
                
        # Calculate metadata score for relevance boosting
        for doc_id, doc_info in combined_dict.items():
            metadata_score = self._calculate_metadata_score(doc_info["metadata"], query_context)
            doc_info["metadata_score"] = metadata_score
        
        # Calculate combined scores
        combined_results = []
        for doc_id, doc_info in combined_dict.items():
            # Apply weights to different score components
            combined_score = (
                self.vector_weight * doc_info["vector_score"] +
                self.keyword_weight * doc_info["keyword_score"] +
                self.metadata_weight * doc_info["metadata_score"]
            )
            
            # Filter out low-scoring results
            if combined_score >= self.min_score:
                combined_results.append(
                    SearchResult(
                        id=doc_id,
                        score=combined_score,
                        content=doc_info["content"],
                        metadata=doc_info["metadata"],
                        vector_score=doc_info["vector_score"],
                        keyword_score=doc_info["keyword_score"]
                    )
                )
        
        # Sort by combined score
        combined_results.sort(key=lambda x: x.score, reverse=True)
        
        # Return top results
        return combined_results[:limit] 