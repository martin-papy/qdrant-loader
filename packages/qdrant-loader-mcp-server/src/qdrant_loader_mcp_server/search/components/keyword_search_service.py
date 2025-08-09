"""Keyword search service for hybrid search."""

import asyncio
import re
from typing import Any

import numpy as np
from qdrant_client import QdrantClient
from rank_bm25 import BM25Okapi

from ...utils.logging import LoggingConfig
from .field_query_parser import FieldQueryParser


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
        self.field_parser = FieldQueryParser()
        self.logger = LoggingConfig.get_logger(__name__)

    async def keyword_search(
        self,
        query: str,
        limit: int,
        project_ids: list[str] | None = None,
        max_candidates: int = 2000,
    ) -> list[dict[str, Any]]:
        """Perform keyword search using BM25.

        Args:
            query: Search query
            limit: Maximum number of results
            project_ids: Optional project ID filters
            max_candidates: Maximum number of candidate documents to fetch from Qdrant before ranking

        Returns:
            List of search results with scores, text, metadata, and source_type
        """
        # ✅ Parse query for field-specific filters
        parsed_query = self.field_parser.parse_query(query)
        self.logger.debug(
            f"Keyword search - parsed query: {len(parsed_query.field_queries)} field queries, text: '{parsed_query.text_query}'"
        )

        # Create filter combining field queries and project IDs
        query_filter = self.field_parser.create_qdrant_filter(
            parsed_query.field_queries, project_ids
        )

        # Determine how many candidates to fetch per page: min(max_candidates, scaled_limit)
        # Using a scale factor to over-fetch relative to requested limit for better ranking quality
        scale_factor = 5
        scaled_limit = max(limit * scale_factor, limit)
        page_limit = min(max_candidates, scaled_limit)

        # Paginate through Qdrant using scroll until we gather up to max_candidates
        all_points = []
        next_offset = None
        total_fetched = 0
        while total_fetched < max_candidates:
            batch_limit = min(page_limit, max_candidates - total_fetched)
            points, next_offset = await self.qdrant_client.scroll(
                collection_name=self.collection_name,
                limit=batch_limit,
                with_payload=True,
                with_vectors=False,
                scroll_filter=query_filter,
                offset=next_offset,
            )

            if not points:
                break

            all_points.extend(points)
            total_fetched += len(points)

            if not next_offset:
                break

        self.logger.debug(
            f"Keyword search - fetched {len(all_points)} candidates (requested max {max_candidates}, limit {limit})"
        )

        documents = []
        metadata_list = []
        source_types = []
        titles = []
        urls = []
        document_ids = []
        sources = []
        created_ats = []
        updated_ats = []

        for point in all_points:
            if point.payload:
                content = point.payload.get("content", "")
                metadata = point.payload.get("metadata", {})
                source_type = point.payload.get("source_type", "unknown")
                # Extract fields directly from Qdrant payload
                title = point.payload.get("title", "")
                url = point.payload.get("url", "")
                document_id = point.payload.get("document_id", "")
                source = point.payload.get("source", "")
                created_at = point.payload.get("created_at", "")
                updated_at = point.payload.get("updated_at", "")

                documents.append(content)
                metadata_list.append(metadata)
                source_types.append(source_type)
                titles.append(title)
                urls.append(url)
                document_ids.append(document_id)
                sources.append(source)
                created_ats.append(created_at)
                updated_ats.append(updated_at)

        if not documents:
            self.logger.warning("No documents found for keyword search")
            return []

        # Handle filter-only searches (no text query for BM25)
        if self.field_parser.should_use_filter_only(parsed_query):
            self.logger.debug(
                "Filter-only search - assigning equal scores to all results"
            )
            # For filter-only searches, assign equal scores to all results
            scores = np.ones(len(documents))
        else:
            # Use BM25 scoring for text queries, offloaded to a thread
            search_query = parsed_query.text_query if parsed_query.text_query else query
            scores = await asyncio.to_thread(
                self._compute_bm25_scores, documents, search_query
            )

        # Stable sort for ranking to keep original order among ties
        top_indices = np.array(
            sorted(range(len(scores)), key=lambda i: (scores[i], i), reverse=True)[
                :limit
            ]
        )

        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                result = {
                    "score": float(scores[idx]),
                    "text": documents[idx],
                    "metadata": metadata_list[idx],
                    "source_type": source_types[idx],
                    # Include extracted fields from Qdrant payload
                    "title": titles[idx],
                    "url": urls[idx],
                    "document_id": document_ids[idx],
                    "source": sources[idx],
                    "created_at": created_ats[idx],
                    "updated_at": updated_ats[idx],
                }

                results.append(result)

        return results

    # Note: _build_filter method removed - now using FieldQueryParser.create_qdrant_filter()

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Tokenize text using regex-based word tokenization and lowercasing."""
        if not isinstance(text, str):
            return []
        return re.findall(r"\b\w+\b", text.lower())

    def _compute_bm25_scores(self, documents: list[str], query: str) -> np.ndarray:
        """Compute BM25 scores for documents against the query.

        Tokenizes documents and query with regex word tokenization and lowercasing.
        """
        tokenized_docs = [self._tokenize(doc) for doc in documents]
        bm25 = BM25Okapi(tokenized_docs)
        tokenized_query = self._tokenize(query)
        return bm25.get_scores(tokenized_query)
