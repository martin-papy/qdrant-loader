"""Hybrid search implementation combining vector and keyword search."""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
from openai import AsyncOpenAI
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.models import Filter, PointStruct, ScoredPoint
from rank_bm25 import BM25Okapi

from .models import SearchResult
from ..utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


@dataclass
class HybridSearchResult:
    """Container for hybrid search results."""

    score: float
    text: str
    source_type: str
    source_title: str
    source_url: str | None = None
    file_path: str | None = None
    repo_name: str | None = None
    vector_score: float = 0.0
    keyword_score: float = 0.0


class HybridSearchEngine:
    """Service for hybrid search combining vector and keyword search."""

    def __init__(
        self,
        qdrant_client: QdrantClient,
        openai_client: AsyncOpenAI,
        collection_name: str,
        vector_weight: float = 0.6,
        keyword_weight: float = 0.3,
        metadata_weight: float = 0.1,
        min_score: float = 0.3,
        dense_vector_name: str = "dense",
        sparse_vector_name: str = "sparse",
        alpha: float = 0.5,
    ):
        """Initialize the hybrid search service.

        Args:
            qdrant_client: Qdrant client instance
            openai_client: OpenAI client instance
            collection_name: Name of the Qdrant collection
            vector_weight: Weight for vector search scores (0-1)
            keyword_weight: Weight for keyword search scores (0-1)
            metadata_weight: Weight for metadata-based scoring (0-1)
            min_score: Minimum combined score threshold
            dense_vector_name: Name of the dense vector field
            sparse_vector_name: Name of the sparse vector field
            alpha: Weight for dense search (1-alpha for sparse search)
        """
        self.qdrant_client = qdrant_client
        self.openai_client = openai_client
        self.collection_name = collection_name
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
        self.metadata_weight = metadata_weight
        self.min_score = min_score
        self.dense_vector_name = dense_vector_name
        self.sparse_vector_name = sparse_vector_name
        self.alpha = alpha
        self.logger = LoggingConfig.get_logger(__name__)

        # Common query expansions for frequently used terms
        self.query_expansions = {
            "product requirements": [
                "PRD",
                "requirements document",
                "product specification",
            ],
            "requirements": ["specs", "requirements document", "features"],
            "architecture": ["system design", "technical architecture"],
            "UI": ["user interface", "frontend", "design"],
            "API": ["interface", "endpoints", "REST"],
            "database": ["DB", "data storage", "persistence"],
            "security": ["auth", "authentication", "authorization"],
        }

    async def _expand_query(self, query: str) -> str:
        """Expand query with related terms for better matching."""
        expanded_query = query
        lower_query = query.lower()

        for key, expansions in self.query_expansions.items():
            if key.lower() in lower_query:
                expansion_terms = " ".join(expansions)
                expanded_query = f"{query} {expansion_terms}"
                self.logger.debug(
                    "Expanded query",
                    original_query=query,
                    expanded_query=expanded_query,
                )
                break

        return expanded_query

    async def _get_embedding(self, text: str) -> list[float]:
        """Get embedding for text using OpenAI."""
        try:
            response = await self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            self.logger.error("Failed to get embedding", error=str(e))
            raise

    async def search(
        self, query: str, limit: int = 5, source_types: list[str] | None = None
    ) -> list[SearchResult]:
        """Perform hybrid search combining vector and keyword search."""
        self.logger.debug(
            "Starting hybrid search",
            query=query,
            limit=limit,
            source_types=source_types,
        )

        try:
            # Expand query with related terms
            expanded_query = await self._expand_query(query)

            # Get vector search results
            vector_results = await self._vector_search(expanded_query, limit * 3)

            # Get keyword search results
            keyword_results = await self._keyword_search(query, limit * 3)

            # Analyze query for context
            query_context = self._analyze_query(query)

            # Combine and rerank results
            combined_results = await self._combine_results(
                vector_results, keyword_results, query_context, limit, source_types
            )

            # Convert to SearchResult objects
            return [
                SearchResult(
                    score=result.score,
                    text=result.text,
                    source_type=result.source_type,
                    source_title=result.source_title,
                    source_url=result.source_url,
                    file_path=result.file_path,
                    repo_name=result.repo_name,
                )
                for result in combined_results
            ]

        except Exception as e:
            self.logger.error("Error in hybrid search", error=str(e), query=query)
            raise

    def _analyze_query(self, query: str) -> dict[str, Any]:
        """Analyze query to determine intent and context."""
        context = {
            "is_question": bool(
                re.search(r"\?|what|how|why|when|who|where", query.lower())
            ),
            "is_broad": len(query.split()) < 5,
            "is_specific": len(query.split()) > 7,
            "probable_intent": "informational",
            "keywords": [
                word.lower() for word in re.findall(r"\b\w{3,}\b", query.lower())
            ],
        }

        lower_query = query.lower()
        if "how to" in lower_query or "steps" in lower_query:
            context["probable_intent"] = "procedural"
        elif any(
            term in lower_query for term in ["requirements", "prd", "specification"]
        ):
            context["probable_intent"] = "requirements"
        elif any(
            term in lower_query for term in ["architecture", "design", "structure"]
        ):
            context["probable_intent"] = "architecture"

        return context

    async def _vector_search(self, query: str, limit: int) -> list[dict[str, Any]]:
        """Perform vector search using Qdrant."""
        query_embedding = await self._get_embedding(query)

        search_params = models.SearchParams(hnsw_ef=128, exact=False)

        results = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=limit,
            score_threshold=self.min_score,
            search_params=search_params,
        )

        return [
            {
                "score": hit.score,
                "text": hit.payload.get("content", "") if hit.payload else "",
                "metadata": hit.payload.get("metadata", {}) if hit.payload else {},
                "source_type": (
                    hit.payload.get("source_type", "unknown")
                    if hit.payload
                    else "unknown"
                ),
            }
            for hit in results
        ]

    async def _keyword_search(self, query: str, limit: int) -> list[dict[str, Any]]:
        """Perform keyword search using BM25."""
        scroll_results = self.qdrant_client.scroll(
            collection_name=self.collection_name,
            limit=10000,
            with_payload=True,
            with_vectors=False,
        )

        documents = []
        metadata_list = []
        source_types = []

        for point in scroll_results[0]:
            if point.payload:
                content = point.payload.get("content", "")
                metadata = point.payload.get("metadata", {})
                source_type = point.payload.get("source_type", "unknown")
                documents.append(content)
                metadata_list.append(metadata)
                source_types.append(source_type)

        tokenized_docs = [doc.split() for doc in documents]
        bm25 = BM25Okapi(tokenized_docs)

        tokenized_query = query.split()
        scores = bm25.get_scores(tokenized_query)

        top_indices = np.argsort(scores)[-limit:][::-1]

        return [
            {
                "score": float(scores[idx]),
                "text": documents[idx],
                "metadata": metadata_list[idx],
                "source_type": source_types[idx],
            }
            for idx in top_indices
            if scores[idx] > 0
        ]

    async def _combine_results(
        self,
        vector_results: list[dict[str, Any]],
        keyword_results: list[dict[str, Any]],
        query_context: dict[str, Any],
        limit: int,
        source_types: list[str] | None = None,
    ) -> list[HybridSearchResult]:
        """Combine and rerank results from vector and keyword search."""
        combined_dict = {}

        # Process vector results
        for result in vector_results:
            text = result["text"]
            if text not in combined_dict:
                metadata = result["metadata"]
                combined_dict[text] = {
                    "text": text,
                    "metadata": metadata,
                    "source_type": result["source_type"],
                    "vector_score": result["score"],
                    "keyword_score": 0.0,
                }

        # Process keyword results
        for result in keyword_results:
            text = result["text"]
            if text in combined_dict:
                combined_dict[text]["keyword_score"] = result["score"]
            else:
                metadata = result["metadata"]
                combined_dict[text] = {
                    "text": text,
                    "metadata": metadata,
                    "source_type": result["source_type"],
                    "vector_score": 0.0,
                    "keyword_score": result["score"],
                }

        # Calculate combined scores and create results
        combined_results = []
        for text, info in combined_dict.items():
            # Skip if source type doesn't match filter
            if source_types and info["source_type"] not in source_types:
                continue

            metadata = info["metadata"]
            combined_score = (
                self.vector_weight * info["vector_score"]
                + self.keyword_weight * info["keyword_score"]
            )

            if combined_score >= self.min_score:
                combined_results.append(
                    HybridSearchResult(
                        score=combined_score,
                        text=text,
                        source_type=info["source_type"],
                        source_title=metadata.get("title", ""),
                        source_url=metadata.get("url"),
                        file_path=metadata.get("file_path"),
                        repo_name=metadata.get("repository_name"),
                        vector_score=info["vector_score"],
                        keyword_score=info["keyword_score"],
                    )
                )

        # Sort by combined score
        combined_results.sort(key=lambda x: x.score, reverse=True)
        return combined_results[:limit]
