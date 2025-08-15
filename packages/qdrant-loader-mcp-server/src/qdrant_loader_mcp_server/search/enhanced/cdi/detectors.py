"""
Conflict Detection for Cross-Document Intelligence.

This module implements advanced conflict detection between documents using
vector similarity analysis and optional LLM validation for comprehensive
conflict identification and analysis.
"""

from __future__ import annotations

import asyncio
import time
import warnings
from collections import Counter, defaultdict
from datetime import datetime
from typing import TYPE_CHECKING, Any

import numpy as np

# Soft-import async clients to avoid hard dependency at import time
if TYPE_CHECKING:
    from openai import AsyncOpenAI
    from qdrant_client import AsyncQdrantClient
else:
    AsyncQdrantClient = None  # type: ignore[assignment]
    AsyncOpenAI = None  # type: ignore[assignment]

from ....utils.logging import LoggingConfig
from ...models import SearchResult
from ...nlp.spacy_analyzer import SpaCyQueryAnalyzer
from .models import ConflictAnalysis

logger = LoggingConfig.get_logger(__name__)


class ConflictDetector:
    """Enhanced conflict detector using vector similarity and LLM validation."""

    def __init__(
        self,
        spacy_analyzer: SpaCyQueryAnalyzer,
        qdrant_client: AsyncQdrantClient | None = None,
        openai_client: AsyncOpenAI | None = None,
        collection_name: str = "documents",
        preferred_vector_name: str | None = "dense",
    ):
        """Initialize the enhanced conflict detector.

        Args:
            spacy_analyzer: SpaCy analyzer for text processing
            qdrant_client: Qdrant client for vector operations
            openai_client: OpenAI client for LLM analysis
            collection_name: Qdrant collection name
        """
        self.spacy_analyzer = spacy_analyzer
        self.qdrant_client = qdrant_client
        self.openai_client = openai_client
        self.collection_name = collection_name
        self.logger = LoggingConfig.get_logger(__name__)
        self.preferred_vector_name = preferred_vector_name

        # Vector similarity thresholds
        self.MIN_VECTOR_SIMILARITY = (
            0.6  # Minimum similarity to consider for conflict analysis
        )
        self.MAX_VECTOR_SIMILARITY = (
            0.95  # Maximum similarity - too similar suggests same content
        )

        # LLM validation settings
        self.llm_enabled = qdrant_client is not None and openai_client is not None

    async def _get_document_embeddings(
        self, document_ids: list[str]
    ) -> dict[str, list[float]]:
        """Retrieve document embeddings from Qdrant."""
        if not self.qdrant_client:
            return {}

        try:
            embeddings = {}
            # Use bounded concurrency and configurable timeouts
            settings = getattr(self, "_settings", {}) if hasattr(self, "_settings") else {}
            timeout_s = settings.get("conflict_embeddings_timeout_s", 5.0)
            max_cc = settings.get("conflict_embeddings_max_concurrency", 5)

            # Create semaphore for concurrency control
            semaphore = asyncio.Semaphore(max_cc)

            async def fetch_embedding(doc_id: str):
                async with semaphore:
                    try:
                        # Search for the document by its ID using a filter
                        search_result = await asyncio.wait_for(
                            self.qdrant_client.scroll(
                                collection_name=self.collection_name,
                                scroll_filter={
                                    "must": [{"key": "document_id", "match": {"value": doc_id}}]
                                },
                                limit=1,
                                with_vectors=True,
                            ),
                            timeout=timeout_s
                        )

                        if search_result and search_result[0]:
                            point = search_result[0][0]
                            if point.vector:
                                # Handle different vector formats
                                if isinstance(point.vector, dict):
                                    # Named vectors
                                    vector_data = (
                                        point.vector.get(self.preferred_vector_name) or
                                        point.vector.get("dense") or
                                        next(iter(point.vector.values()), None)
                                    )
                                else:
                                    # Single vector
                                    vector_data = point.vector

                                if vector_data:
                                    embeddings[doc_id] = vector_data
                                    self.logger.debug(f"Retrieved embedding for document {doc_id}")
                                else:
                                    self.logger.warning(f"No vector data found for document {doc_id}")
                            else:
                                self.logger.warning(f"No vectors found for document {doc_id}")
                    except asyncio.TimeoutError:
                        self.logger.warning(f"Timeout retrieving embedding for document {doc_id}")
                    except Exception as e:
                        self.logger.error(f"Error retrieving embedding for document {doc_id}: {e}")

            # Execute fetches with concurrency control
            await asyncio.gather(
                *[fetch_embedding(doc_id) for doc_id in document_ids],
                return_exceptions=True
            )

            self.logger.debug(f"Retrieved embeddings for {len(embeddings)}/{len(document_ids)} documents")
            return embeddings

        except Exception as e:
            self.logger.error(f"Error retrieving document embeddings: {e}")
            return {}

    def _calculate_vector_similarity(
        self, embedding1: list[float], embedding2: list[float]
    ) -> float:
        """Calculate cosine similarity between two vectors."""
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)

            # Calculate cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = dot_product / (norm1 * norm2)
            return float(np.clip(similarity, -1.0, 1.0))

        except Exception as e:
            self.logger.error(f"Error calculating vector similarity: {e}")
            return 0.0

    async def _validate_conflict_with_llm(
        self, doc1: SearchResult, doc2: SearchResult, similarity_score: float
    ) -> tuple[bool, str, float]:
        """Use LLM to validate potential conflicts."""
        if not self.openai_client:
            return False, "LLM validation not available", 0.0

        try:
            prompt = f"""
            Analyze these two documents for conflicts in information, recommendations, or approaches:

            Document 1: {doc1.source_title}
            Content: {doc1.content[:1000]}...
            
            Document 2: {doc2.source_title}
            Content: {doc2.content[:1000]}...

            Vector Similarity: {similarity_score:.3f}

            Respond with:
            1. CONFLICT_DETECTED: yes/no
            2. CONFIDENCE: 0.0-1.0
            3. EXPLANATION: Brief explanation of the conflict or lack thereof

            Format: CONFLICT_DETECTED|CONFIDENCE|EXPLANATION
            """

            # Use settings-based configuration if available
            settings = getattr(self, "_settings", {}) if hasattr(self, "_settings") else {}
            timeout_s = settings.get("conflict_llm_timeout_s", 10.0)

            response = await asyncio.wait_for(
                self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=200,
                    temperature=0.1,
                ),
                timeout=timeout_s
            )

            content = response.choices[0].message.content.strip()
            parts = content.split("|")

            if len(parts) >= 3:
                conflict_detected = parts[0].lower().strip() == "yes"
                confidence = float(parts[1].strip())
                explanation = parts[2].strip()
                return conflict_detected, explanation, confidence
            else:
                return False, "Invalid LLM response format", 0.0

        except asyncio.TimeoutError:
            self.logger.warning("LLM conflict validation timed out")
            return False, "LLM validation timeout", 0.0
        except Exception as e:
            self.logger.error(f"Error in LLM conflict validation: {e}")
            return False, f"LLM validation error: {str(e)}", 0.0

    def _analyze_text_conflicts(self, doc1: SearchResult, doc2: SearchResult) -> tuple[bool, str, float]:
        """Analyze textual conflicts using spaCy-based analysis."""
        try:
            # Use spaCy to extract key statements and compare them
            doc1_analysis = self.spacy_analyzer.analyze_query_semantic(doc1.content)
            doc2_analysis = self.spacy_analyzer.analyze_query_semantic(doc2.content)

            # Look for conflicting keywords and entities
            doc1_entities = set(ent[0].lower() for ent in doc1_analysis.entities)
            doc2_entities = set(ent[0].lower() for ent in doc2_analysis.entities)

            doc1_keywords = set(kw.lower() for kw in doc1_analysis.semantic_keywords)
            doc2_keywords = set(kw.lower() for kw in doc2_analysis.semantic_keywords)

            # Calculate overlap
            entity_overlap = len(doc1_entities & doc2_entities) / max(
                len(doc1_entities | doc2_entities), 1
            )
            keyword_overlap = len(doc1_keywords & doc2_keywords) / max(
                len(doc1_keywords | doc2_keywords), 1
            )

            # Detect potential conflicts based on similar topics but different recommendations
            conflict_indicators = [
                "should not",
                "avoid",
                "deprecated",
                "recommended",
                "best practice",
                "anti-pattern",
                "wrong",
                "correct",
                "instead",
                "better",
                "worse",
            ]

            doc1_indicators = sum(
                1 for indicator in conflict_indicators if indicator in doc1.content.lower()
            )
            doc2_indicators = sum(
                1 for indicator in conflict_indicators if indicator in doc2.content.lower()
            )

            # High overlap with conflicting language suggests potential conflict
            if entity_overlap > 0.3 and (doc1_indicators > 0 or doc2_indicators > 0):
                confidence = min(entity_overlap * (doc1_indicators + doc2_indicators) / 10, 1.0)
                explanation = f"Similar topics with conflicting recommendations (overlap: {entity_overlap:.2f})"
                return True, explanation, confidence

            return False, "No textual conflicts detected", 0.0

        except Exception as e:
            self.logger.error(f"Error in text conflict analysis: {e}")
            return False, f"Text analysis error: {str(e)}", 0.0

    def _analyze_metadata_conflicts(self, doc1: SearchResult, doc2: SearchResult) -> tuple[bool, str, float]:
        """Analyze metadata-based conflicts."""
        try:
            conflicts = []
            total_weight = 0

            # Check creation dates for outdated information
            doc1_date = getattr(doc1, "created_at", None)
            doc2_date = getattr(doc2, "created_at", None)

            if doc1_date and doc2_date:
                date_diff = abs((doc1_date - doc2_date).days)
                if date_diff > 365:  # More than 1 year difference
                    conflicts.append(("date_conflict", 0.3, f"Documents created {date_diff} days apart"))
                    total_weight += 0.3

            # Check source types for potential conflicts
            if doc1.source_type != doc2.source_type:
                source_conflicts = {
                    ("confluence", "git"): 0.2,  # Wiki vs code documentation
                    ("jira", "confluence"): 0.1,  # Tickets vs documentation
                }
                conflict_key = tuple(sorted([doc1.source_type, doc2.source_type]))
                if conflict_key in source_conflicts:
                    weight = source_conflicts[conflict_key]
                    conflicts.append(("source_type_conflict", weight, f"Different source types: {conflict_key}"))
                    total_weight += weight

            # Check project conflicts
            if hasattr(doc1, "project_id") and hasattr(doc2, "project_id"):
                if doc1.project_id != doc2.project_id:
                    conflicts.append(("project_conflict", 0.1, f"Different projects: {doc1.project_id} vs {doc2.project_id}"))
                    total_weight += 0.1

            if conflicts and total_weight > 0.2:
                explanation = "; ".join([conflict[2] for conflict in conflicts])
                return True, explanation, min(total_weight, 1.0)

            return False, "No metadata conflicts detected", 0.0

        except Exception as e:
            self.logger.error(f"Error in metadata conflict analysis: {e}")
            return False, f"Metadata analysis error: {str(e)}", 0.0

    async def detect_conflicts(self, documents: list[SearchResult]) -> list[ConflictAnalysis]:
        """Detect conflicts between documents using multiple analysis methods."""
        start_time = time.time()
        conflicts = []

        if len(documents) < 2:
            self.logger.debug("Need at least 2 documents for conflict detection")
            return conflicts

        try:
            # Get document embeddings for vector similarity analysis
            document_ids = [getattr(doc, "document_id", f"{doc.source_type}:{doc.source_title}") for doc in documents]
            embeddings = await self._get_document_embeddings(document_ids)

            # Compare all pairs of documents
            for i, doc1 in enumerate(documents):
                for j, doc2 in enumerate(documents[i + 1:], i + 1):
                    doc1_id = document_ids[i]
                    doc2_id = document_ids[j]

                    # Vector similarity analysis (if embeddings available)
                    vector_similarity = 0.0
                    if doc1_id in embeddings and doc2_id in embeddings:
                        vector_similarity = self._calculate_vector_similarity(
                            embeddings[doc1_id], embeddings[doc2_id]
                        )

                        # Skip if vectors are too similar (likely same content) or too dissimilar
                        if (
                            vector_similarity > self.MAX_VECTOR_SIMILARITY
                            or vector_similarity < self.MIN_VECTOR_SIMILARITY
                        ):
                            continue

                    # Text-based conflict analysis
                    text_conflict, text_explanation, text_confidence = self._analyze_text_conflicts(doc1, doc2)

                    # Metadata-based conflict analysis  
                    metadata_conflict, metadata_explanation, metadata_confidence = self._analyze_metadata_conflicts(doc1, doc2)

                    # LLM validation (if enabled and vector similarity suggests potential conflict)
                    llm_conflict = False
                    llm_explanation = ""
                    llm_confidence = 0.0

                    if self.llm_enabled and (text_conflict or metadata_conflict or vector_similarity > 0.7):
                        llm_conflict, llm_explanation, llm_confidence = await self._validate_conflict_with_llm(
                            doc1, doc2, vector_similarity
                        )

                    # Determine overall conflict
                    if text_conflict or metadata_conflict or llm_conflict:
                        # Combine confidence scores
                        combined_confidence = max(text_confidence, metadata_confidence, llm_confidence)

                        # Create conflict analysis
                        analysis = ConflictAnalysis(
                            document1_title=doc1.source_title,
                            document1_source=doc1.source_type,
                            document2_title=doc2.source_title,
                            document2_source=doc2.source_type,
                            conflict_type="content_conflict",
                            confidence_score=combined_confidence,
                            vector_similarity=vector_similarity,
                            analysis_method="multi_method",
                            explanation=f"Text: {text_explanation}; Metadata: {metadata_explanation}; LLM: {llm_explanation}",
                            detected_at=datetime.now(),
                        )

                        conflicts.append(analysis)

            processing_time = (time.time() - start_time) * 1000
            self.logger.info(
                f"Conflict detection completed in {processing_time:.2f}ms",
                document_count=len(documents),
                conflicts_detected=len(conflicts),
                vector_analysis=len(embeddings) > 0,
                llm_analysis=self.llm_enabled,
            )

            return conflicts

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            self.logger.error(f"Error in conflict detection after {processing_time:.2f}ms: {e}")
            return []
