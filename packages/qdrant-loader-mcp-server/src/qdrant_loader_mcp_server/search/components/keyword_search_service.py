"""Keyword search service for hybrid search."""

from typing import Any

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models
from rank_bm25 import BM25Okapi

from ...utils.logging import LoggingConfig


class KeywordSearchService:
    """Handles keyword search operations using BM25."""

    def __init__(
        self,
        qdrant_client: QdrantClient,
        collection_name: str,
    ):
        """Initialize the keyword search service.
        
        Args:
            qdrant_client: Qdrant client instance
            collection_name: Name of the Qdrant collection
        """
        self.qdrant_client = qdrant_client
        self.collection_name = collection_name
        self.logger = LoggingConfig.get_logger(__name__)

    async def keyword_search(
        self, 
        query: str, 
        limit: int, 
        project_ids: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Perform keyword search using BM25.
        
        Args:
            query: Search query
            limit: Maximum number of results
            project_ids: Optional project ID filters
            
        Returns:
            List of search results with scores, text, metadata, and source_type
        """
        scroll_results = await self.qdrant_client.scroll(
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

        if not documents:
            self.logger.warning("No documents found for keyword search")
            return []

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