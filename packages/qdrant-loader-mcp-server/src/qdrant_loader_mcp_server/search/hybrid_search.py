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

    # Project information (for multi-project support)
    project_id: str | None = None
    project_name: str | None = None
    project_description: str | None = None
    collection_name: str | None = None

    # Hierarchy information (primarily for Confluence)
    parent_id: str | None = None
    parent_title: str | None = None
    breadcrumb_text: str | None = None
    depth: int | None = None
    children_count: int | None = None
    hierarchy_context: str | None = None

    # Attachment information (for files attached to documents)
    is_attachment: bool = False
    parent_document_id: str | None = None
    parent_document_title: str | None = None
    attachment_id: str | None = None
    original_filename: str | None = None
    file_size: int | None = None
    mime_type: str | None = None
    attachment_author: str | None = None
    attachment_context: str | None = None


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
        self,
        query: str,
        limit: int = 5,
        source_types: list[str] | None = None,
        project_ids: list[str] | None = None,
    ) -> list[SearchResult]:
        """Perform hybrid search combining vector and keyword search.

        Args:
            query: Search query text
            limit: Maximum number of results to return
            source_types: Optional list of source types to filter by
            project_ids: Optional list of project IDs to filter by
        """
        self.logger.debug(
            "Starting hybrid search",
            query=query,
            limit=limit,
            source_types=source_types,
            project_ids=project_ids,
        )

        try:
            # Expand query with related terms
            expanded_query = await self._expand_query(query)

            # Get vector search results
            vector_results = await self._vector_search(
                expanded_query, limit * 3, project_ids
            )

            # Get keyword search results
            keyword_results = await self._keyword_search(query, limit * 3, project_ids)

            # Analyze query for context
            query_context = self._analyze_query(query)

            # Combine and rerank results
            combined_results = await self._combine_results(
                vector_results,
                keyword_results,
                query_context,
                limit,
                source_types,
                project_ids,
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
                    project_id=result.project_id,
                    project_name=result.project_name,
                    project_description=result.project_description,
                    collection_name=result.collection_name,
                    parent_id=result.parent_id,
                    parent_title=result.parent_title,
                    breadcrumb_text=result.breadcrumb_text,
                    depth=result.depth,
                    children_count=result.children_count,
                    hierarchy_context=result.hierarchy_context,
                    is_attachment=result.is_attachment,
                    parent_document_id=result.parent_document_id,
                    parent_document_title=result.parent_document_title,
                    attachment_id=result.attachment_id,
                    original_filename=result.original_filename,
                    file_size=result.file_size,
                    mime_type=result.mime_type,
                    attachment_author=result.attachment_author,
                    attachment_context=result.attachment_context,
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

    async def _vector_search(
        self, query: str, limit: int, project_ids: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Perform vector search using Qdrant."""
        query_embedding = await self._get_embedding(query)

        search_params = models.SearchParams(hnsw_ef=128, exact=False)

        results = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=limit,
            score_threshold=self.min_score,
            search_params=search_params,
            query_filter=self._build_filter(project_ids),
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

    async def _keyword_search(
        self, query: str, limit: int, project_ids: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Perform keyword search using BM25."""
        scroll_results = self.qdrant_client.scroll(
            collection_name=self.collection_name,
            limit=10000,
            with_payload=True,
            with_vectors=False,
            scroll_filter=self._build_filter(project_ids),
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
        project_ids: list[str] | None = None,
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
                # Extract hierarchy information
                hierarchy_info = self._extract_metadata_info(metadata)

                # Extract project information
                project_info = self._extract_project_info(metadata)

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
                        project_id=project_info["project_id"],
                        project_name=project_info["project_name"],
                        project_description=project_info["project_description"],
                        collection_name=project_info["collection_name"],
                        parent_id=hierarchy_info["parent_id"],
                        parent_title=hierarchy_info["parent_title"],
                        breadcrumb_text=hierarchy_info["breadcrumb_text"],
                        depth=hierarchy_info["depth"],
                        children_count=hierarchy_info["children_count"],
                        hierarchy_context=hierarchy_info["hierarchy_context"],
                        is_attachment=hierarchy_info["is_attachment"],
                        parent_document_id=hierarchy_info["parent_document_id"],
                        parent_document_title=hierarchy_info["parent_document_title"],
                        attachment_id=hierarchy_info["attachment_id"],
                        original_filename=hierarchy_info["original_filename"],
                        file_size=hierarchy_info["file_size"],
                        mime_type=hierarchy_info["mime_type"],
                        attachment_author=hierarchy_info["attachment_author"],
                        attachment_context=hierarchy_info["attachment_context"],
                    )
                )

        # Sort by combined score
        combined_results.sort(key=lambda x: x.score, reverse=True)
        return combined_results[:limit]

    def _extract_metadata_info(self, metadata: dict) -> dict:
        """Extract hierarchy and attachment information from document metadata.

        Args:
            metadata: Document metadata

        Returns:
            Dictionary with hierarchy and attachment information
        """
        # Extract hierarchy information
        hierarchy_info = {
            "parent_id": metadata.get("parent_id"),
            "parent_title": metadata.get("parent_title"),
            "breadcrumb_text": metadata.get("breadcrumb_text"),
            "depth": metadata.get("depth"),
            "children_count": None,
            "hierarchy_context": None,
        }

        # Calculate children count
        children = metadata.get("children", [])
        if children:
            hierarchy_info["children_count"] = len(children)

        # Generate hierarchy context for display
        if metadata.get("breadcrumb_text") or metadata.get("depth") is not None:
            context_parts = []

            if metadata.get("breadcrumb_text"):
                context_parts.append(f"Path: {metadata.get('breadcrumb_text')}")

            if metadata.get("depth") is not None:
                context_parts.append(f"Depth: {metadata.get('depth')}")

            if (
                hierarchy_info["children_count"] is not None
                and hierarchy_info["children_count"] > 0
            ):
                context_parts.append(f"Children: {hierarchy_info['children_count']}")

            if context_parts:
                hierarchy_info["hierarchy_context"] = " | ".join(context_parts)

        # Extract attachment information
        attachment_info = {
            "is_attachment": metadata.get("is_attachment", False),
            "parent_document_id": metadata.get("parent_document_id"),
            "parent_document_title": metadata.get("parent_document_title"),
            "attachment_id": metadata.get("attachment_id"),
            "original_filename": metadata.get("original_filename"),
            "file_size": metadata.get("file_size"),
            "mime_type": metadata.get("mime_type"),
            "attachment_author": metadata.get("attachment_author")
            or metadata.get("author"),
            "attachment_context": None,
        }

        # Generate attachment context for display
        if attachment_info["is_attachment"]:
            context_parts = []

            if attachment_info["original_filename"]:
                context_parts.append(f"File: {attachment_info['original_filename']}")

            if attachment_info["file_size"]:
                # Convert bytes to human readable format
                size = attachment_info["file_size"]
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                elif size < 1024 * 1024 * 1024:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
                else:
                    size_str = f"{size / (1024 * 1024 * 1024):.1f} GB"
                context_parts.append(f"Size: {size_str}")

            if attachment_info["mime_type"]:
                context_parts.append(f"Type: {attachment_info['mime_type']}")

            if attachment_info["attachment_author"]:
                context_parts.append(f"Author: {attachment_info['attachment_author']}")

            if context_parts:
                attachment_info["attachment_context"] = " | ".join(context_parts)

        # Combine both hierarchy and attachment info
        return {**hierarchy_info, **attachment_info}

    def _extract_project_info(self, metadata: dict) -> dict:
        """Extract project information from document metadata.

        Args:
            metadata: Document metadata

        Returns:
            Dictionary with project information
        """
        return {
            "project_id": metadata.get("project_id"),
            "project_name": metadata.get("project_name"),
            "project_description": metadata.get("project_description"),
            "collection_name": metadata.get("collection_name"),
        }

    def _build_filter(
        self, project_ids: list[str] | None = None
    ) -> models.Filter | None:
        """Build a Qdrant filter based on project IDs."""
        if not project_ids:
            return None

        return models.Filter(
            must=[
                models.FieldCondition(
                    key="project_id", match=models.MatchAny(any=project_ids)
                )
            ]
        )
