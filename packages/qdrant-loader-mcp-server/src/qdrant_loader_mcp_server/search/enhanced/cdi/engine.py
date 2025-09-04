"""
Cross-Document Intelligence Engine.

This module implements the main orchestration engine that coordinates all
cross-document intelligence analysis including similarity calculation,
clustering, citation networks, complementary content discovery, and conflict detection.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

# Soft-import async clients to avoid hard dependency at import time
if TYPE_CHECKING:
    pass

from ....utils.logging import LoggingConfig
from ...models import SearchResult
from ...nlp.spacy_analyzer import SpaCyQueryAnalyzer
from .analyzers import DocumentClusterAnalyzer
from .calculators import DocumentSimilarityCalculator
from .citations import CitationNetworkAnalyzer
from .detectors import ConflictDetector
from .extractors.clustering import DefaultClusterer
from .extractors.graph import DefaultGraphBuilder
from .extractors.similarity import DefaultSimilarityComputer
from .finders import ComplementaryContentFinder
from .models import ClusteringStrategy, RelationshipType
from .pipeline import CrossDocumentPipeline
from .rankers.default import DefaultRanker

logger = LoggingConfig.get_logger(__name__)


class CrossDocumentIntelligenceEngine:
    """Main engine that orchestrates cross-document intelligence analysis."""

    def __init__(
        self,
        spacy_analyzer: SpaCyQueryAnalyzer,
        knowledge_graph=None,
        qdrant_client=None,
        openai_client=None,
        collection_name: str = "documents",
        conflict_settings: dict | None = None,
    ):
        """Initialize the cross-document intelligence engine."""
        self.spacy_analyzer = spacy_analyzer
        self.knowledge_graph = knowledge_graph
        self.qdrant_client = qdrant_client
        self.openai_client = openai_client
        self.collection_name = collection_name
        self.logger = LoggingConfig.get_logger(__name__)

        # Initialize pipeline-based composition (behavior preserved via adapters)
        self._pipeline = CrossDocumentPipeline(
            similarity_computer=DefaultSimilarityComputer(spacy_analyzer),
            clusterer=DefaultClusterer(
                similarity_calculator=DocumentSimilarityCalculator(spacy_analyzer)
            ),
            graph_builder=DefaultGraphBuilder(),
            ranker=DefaultRanker(),
        )

        # Keep legacy attributes for backward compatibility across the codebase
        self.similarity_calculator = DocumentSimilarityCalculator(spacy_analyzer)
        self.cluster_analyzer = DocumentClusterAnalyzer(self.similarity_calculator)
        self.citation_analyzer = CitationNetworkAnalyzer()
        self.complementary_finder = ComplementaryContentFinder(
            self.similarity_calculator, knowledge_graph
        )
        self.conflict_detector = ConflictDetector(
            spacy_analyzer, qdrant_client, openai_client, collection_name
        )
        # Optional: LLM provider from core (set by builder)
        self.llm_provider = None
        if conflict_settings is not None:
            validated = self._validate_and_normalize_conflict_settings(
                conflict_settings
            )
            if validated is not None:
                # Apply configuration knobs where supported (respect OpenAI client availability)
                self.conflict_detector.llm_enabled = bool(
                    validated.get("conflict_use_llm", True)
                ) and (openai_client is not None)
                # Store normalized runtime settings for detector use
                self.conflict_detector._settings = validated
            else:
                # Validation already logged a clear warning; keep detector defaults
                pass

    def _validate_and_normalize_conflict_settings(
        self, settings: object
    ) -> dict[str, Any] | None:
        """Validate and normalize conflict detection settings.

        Returns a sanitized settings dict or None when invalid. On any validation
        problem, logs a clear warning and falls back to detector defaults.
        """
        from collections.abc import Mapping

        if not isinstance(settings, Mapping):
            self.logger.warning(
                f"Invalid conflict_settings: expected mapping, got {type(settings).__name__}; using defaults"
            )
            return None

        errors: list[str] = []

        def coerce_bool(value: object, default: bool, key: str) -> bool:
            try:
                if isinstance(value, bool):
                    return value
                if isinstance(value, int | float):
                    return value != 0
                if isinstance(value, str):
                    v = value.strip().lower()
                    if v in {"true", "1", "yes", "y", "on"}:
                        return True
                    if v in {"false", "0", "no", "n", "off"}:
                        return False
                raise ValueError("unrecognized boolean value")
            except Exception as e:
                errors.append(f"{key}: {e}")
                return default

        def coerce_int_non_negative(value: object, default: int, key: str) -> int:
            try:
                if isinstance(value, bool):
                    # Avoid treating booleans as ints
                    raise ValueError("boolean not allowed for integer field")
                if isinstance(value, int | float):
                    v = int(value)
                elif isinstance(value, str):
                    v = int(value.strip())
                else:
                    raise ValueError("unsupported type")
                return v if v >= 0 else default
            except Exception as e:
                errors.append(f"{key}: {e}")
                return default

        def coerce_float_positive(value: object, default: float, key: str) -> float:
            try:
                if isinstance(value, bool):
                    raise ValueError("boolean not allowed for float field")
                if isinstance(value, int | float):
                    v = float(value)
                elif isinstance(value, str):
                    v = float(value.strip())
                else:
                    raise ValueError("unsupported type")
                return v if v > 0 else default
            except Exception as e:
                errors.append(f"{key}: {e}")
                return default

        # Safe defaults align with ConflictDetector fallbacks
        defaults: dict[str, Any] = {
            "conflict_use_llm": True,
            "conflict_max_llm_pairs": 2,
            "conflict_llm_model": "gpt-4o-mini",
            "conflict_llm_timeout_s": 12.0,
            "conflict_overall_timeout_s": 9.0,
            "conflict_text_window_chars": 2000,
            "conflict_max_pairs_total": 24,
            "conflict_embeddings_timeout_s": 5.0,
            "conflict_embeddings_max_concurrency": 5,
            # Optional/unused in detector but supported upstream
            "conflict_limit_default": 10,
            "conflict_tier_caps": {
                "primary": 50,
                "secondary": 30,
                "tertiary": 20,
                "fallback": 10,
            },
        }

        # Start with defaults and override with sanitized values
        normalized: dict[str, Any] = dict(defaults)

        # Booleans
        normalized["conflict_use_llm"] = coerce_bool(
            settings.get("conflict_use_llm", defaults["conflict_use_llm"]),
            defaults["conflict_use_llm"],
            "conflict_use_llm",
        )

        # Integers (non-negative)
        normalized["conflict_max_llm_pairs"] = coerce_int_non_negative(
            settings.get("conflict_max_llm_pairs", defaults["conflict_max_llm_pairs"]),
            defaults["conflict_max_llm_pairs"],
            "conflict_max_llm_pairs",
        )
        normalized["conflict_max_pairs_total"] = coerce_int_non_negative(
            settings.get(
                "conflict_max_pairs_total", defaults["conflict_max_pairs_total"]
            ),
            defaults["conflict_max_pairs_total"],
            "conflict_max_pairs_total",
        )
        normalized["conflict_text_window_chars"] = coerce_int_non_negative(
            settings.get(
                "conflict_text_window_chars", defaults["conflict_text_window_chars"]
            ),
            defaults["conflict_text_window_chars"],
            "conflict_text_window_chars",
        )
        normalized["conflict_embeddings_max_concurrency"] = coerce_int_non_negative(
            settings.get(
                "conflict_embeddings_max_concurrency",
                defaults["conflict_embeddings_max_concurrency"],
            ),
            defaults["conflict_embeddings_max_concurrency"],
            "conflict_embeddings_max_concurrency",
        )
        normalized["conflict_limit_default"] = coerce_int_non_negative(
            settings.get("conflict_limit_default", defaults["conflict_limit_default"]),
            defaults["conflict_limit_default"],
            "conflict_limit_default",
        )

        # Floats (positive)
        normalized["conflict_llm_timeout_s"] = coerce_float_positive(
            settings.get("conflict_llm_timeout_s", defaults["conflict_llm_timeout_s"]),
            defaults["conflict_llm_timeout_s"],
            "conflict_llm_timeout_s",
        )
        normalized["conflict_overall_timeout_s"] = coerce_float_positive(
            settings.get(
                "conflict_overall_timeout_s", defaults["conflict_overall_timeout_s"]
            ),
            defaults["conflict_overall_timeout_s"],
            "conflict_overall_timeout_s",
        )
        normalized["conflict_embeddings_timeout_s"] = coerce_float_positive(
            settings.get(
                "conflict_embeddings_timeout_s",
                defaults["conflict_embeddings_timeout_s"],
            ),
            defaults["conflict_embeddings_timeout_s"],
            "conflict_embeddings_timeout_s",
        )

        # Strings
        llm_model = settings.get("conflict_llm_model", defaults["conflict_llm_model"])
        if isinstance(llm_model, str) and llm_model.strip():
            normalized["conflict_llm_model"] = llm_model.strip()
        else:
            if "conflict_llm_model" in settings:
                errors.append("conflict_llm_model: expected non-empty string")
            normalized["conflict_llm_model"] = defaults["conflict_llm_model"]

        # Nested mapping: conflict_tier_caps
        tier_caps_default = defaults["conflict_tier_caps"]
        tier_caps_value = settings.get("conflict_tier_caps", tier_caps_default)
        if isinstance(tier_caps_value, Mapping):
            tier_caps_normalized: dict[str, int] = dict(tier_caps_default)
            for k in ("primary", "secondary", "tertiary", "fallback"):
                tier_caps_normalized[k] = coerce_int_non_negative(
                    tier_caps_value.get(k, tier_caps_default[k]),
                    tier_caps_default[k],
                    f"conflict_tier_caps.{k}",
                )
            normalized["conflict_tier_caps"] = tier_caps_normalized
        else:
            if "conflict_tier_caps" in settings:
                errors.append("conflict_tier_caps: expected mapping with integer caps")
            normalized["conflict_tier_caps"] = dict(tier_caps_default)

        if errors:
            self.logger.warning(
                "Invalid values in conflict_settings; using defaults for invalid fields: "
                + "; ".join(errors)
            )

        return normalized

    def analyze_document_relationships(self, documents) -> dict[str, Any]:
        """Lightweight relationship analysis focusing on essential relationships."""
        start_time = time.time()

        self.logger.info(
            f"Starting lightweight cross-document analysis for {len(documents)} documents"
        )

        # Skip heavy analysis components for performance:
        # - Skip similarity matrix computation (O(n²) operation)
        # - Skip citation network analysis
        # - Skip complementary content analysis
        # - Skip conflict detection

        # Keep only: document clustering for essential relationships
        clusters = self.cluster_analyzer.create_clusters(
            documents,
            strategy=ClusteringStrategy.MIXED_FEATURES,
            max_clusters=5,  # Reduced from 10 to 5 for faster processing
            min_cluster_size=2,
        )

        processing_time = (time.time() - start_time) * 1000

        # Build lightweight response focused on cluster relationships
        # Need to include documents in clusters for relationship extraction
        cluster_data = []
        doc_id_to_doc = {}

        # Create document lookup for mapping cluster document IDs to actual documents
        for doc in documents:
            doc_id = f"{doc.source_type}:{doc.source_title}"
            doc_id_to_doc[doc_id] = doc

        for cluster in clusters:
            cluster_summary = cluster.get_cluster_summary()

            # Add actual document objects for relationship extraction
            cluster_documents = []
            for doc_id in cluster.documents:
                if doc_id in doc_id_to_doc:
                    doc = doc_id_to_doc[doc_id]
                    cluster_documents.append(
                        {
                            "document_id": doc.document_id,
                            "title": doc.source_title,
                            "source_title": doc.source_title,
                            "source_type": doc.source_type,
                        }
                    )

            cluster_summary["documents"] = cluster_documents
            cluster_data.append(cluster_summary)

        analysis_results = {
            "summary": {
                "total_documents": len(documents),
                "processing_time_ms": processing_time,
                "clusters_found": len(clusters),
                "analysis_mode": "lightweight",
            },
            "document_clusters": cluster_data,
            "relationships_count": sum(
                len(cluster.documents) * (len(cluster.documents) - 1) // 2
                for cluster in clusters
                if len(cluster.documents) > 1
            ),
        }

        self.logger.info(
            f"Lightweight cross-document analysis completed in {processing_time:.2f}ms"
        )

        return analysis_results

    def find_document_relationships(
        self,
        target_doc_id: str,
        documents: list[SearchResult],
        relationship_types: list[RelationshipType] = None,
    ) -> dict[str, list[dict[str, Any]]]:
        """Find specific relationships for a target document."""
        if relationship_types is None:
            relationship_types = [
                RelationshipType.SEMANTIC_SIMILARITY,
                RelationshipType.COMPLEMENTARY,
                RelationshipType.HIERARCHICAL,
            ]

        # Find target document
        target_doc = None
        for doc in documents:
            if f"{doc.source_type}:{doc.source_title}" == target_doc_id:
                target_doc = doc
                break

        if not target_doc:
            return {"error": "Target document not found"}

        relationships = {rel_type.value: [] for rel_type in relationship_types}

        for rel_type in relationship_types:
            if rel_type == RelationshipType.SEMANTIC_SIMILARITY:
                # Find similar documents
                for doc in documents:
                    if doc != target_doc:
                        similarity = self.similarity_calculator.calculate_similarity(
                            target_doc, doc
                        )
                        if similarity.similarity_score > 0.5:
                            relationships[rel_type.value].append(
                                {
                                    "document_id": f"{doc.source_type}:{doc.source_title}",
                                    "score": similarity.similarity_score,
                                    "explanation": similarity.get_display_explanation(),
                                }
                            )

            elif rel_type == RelationshipType.COMPLEMENTARY:
                # Find complementary content
                complementary = self.complementary_finder.find_complementary_content(
                    target_doc, documents
                )
                relationships[rel_type.value] = complementary.get_top_recommendations(5)

            elif rel_type == RelationshipType.HIERARCHICAL:
                # Find hierarchical relationships
                for doc in documents:
                    if doc != target_doc:
                        if (
                            doc.parent_id == target_doc_id
                            or target_doc.parent_id
                            == f"{doc.source_type}:{doc.source_title}"
                        ):
                            relationships[rel_type.value].append(
                                {
                                    "document_id": f"{doc.source_type}:{doc.source_title}",
                                    "relationship": (
                                        "parent"
                                        if doc.parent_id == target_doc_id
                                        else "child"
                                    ),
                                    "explanation": "Direct hierarchical relationship",
                                }
                            )

        # Sort each relationship type by score/relevance
        for rel_type in relationships:
            if relationships[rel_type]:
                relationships[rel_type] = sorted(
                    relationships[rel_type],
                    key=lambda x: x.get("score", x.get("relevance_score", 0)),
                    reverse=True,
                )[
                    :5
                ]  # Top 5 for each type

        return relationships

    def _build_similarity_matrix(
        self, documents: list[SearchResult]
    ) -> dict[str, dict[str, float]]:
        """Build similarity matrix for all document pairs."""
        matrix = {}

        for i, doc1 in enumerate(documents):
            doc1_id = f"{doc1.source_type}:{doc1.source_title}"
            matrix[doc1_id] = {}

            for j, doc2 in enumerate(documents):
                doc2_id = f"{doc2.source_type}:{doc2.source_title}"

                if i == j:
                    matrix[doc1_id][doc2_id] = 1.0
                else:
                    # Ensure rows exist before accessing for symmetry checks
                    if doc2_id not in matrix:
                        matrix[doc2_id] = {}
                    # If symmetric value already computed, reuse it
                    if doc1_id in matrix.get(doc2_id, {}):
                        matrix[doc1_id][doc2_id] = matrix[doc2_id][doc1_id]
                        continue
                    # Otherwise compute and store symmetrically
                    similarity = self.similarity_calculator.calculate_similarity(
                        doc1, doc2
                    )
                    score = similarity.similarity_score
                    matrix[doc1_id][doc2_id] = score
                    matrix[doc2_id][doc1_id] = score

        return matrix

    def _extract_similarity_insights(
        self, similarity_matrix: dict[str, dict[str, float]]
    ) -> dict[str, Any]:
        """Extract insights from the similarity matrix."""
        if not similarity_matrix:
            return {}

        all_scores = []
        for doc1_scores in similarity_matrix.values():
            for _doc2_id, score in doc1_scores.items():
                if score < 1.0:  # Exclude self-similarity
                    all_scores.append(score)

        if not all_scores:
            return {}

        insights = {
            "average_similarity": sum(all_scores) / len(all_scores),
            "max_similarity": max(all_scores),
            "min_similarity": min(all_scores),
            "high_similarity_pairs": sum(1 for score in all_scores if score > 0.7),
            "total_pairs_analyzed": len(all_scores),
        }
        # Alias for tests expecting 'highly_similar_pairs'
        insights["highly_similar_pairs"] = insights["high_similarity_pairs"]

        return insights
