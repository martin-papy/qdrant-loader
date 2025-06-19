"""Result fusion engine for the enhanced hybrid search."""

import hashlib

from ...utils.logging import LoggingConfig
from .models import (
    EnhancedSearchConfig,
    EnhancedSearchResult,
    FusionStrategy,
    QueryWeights,
)


class ResultFusionEngine:
    """Engine for fusing results from multiple search modules."""

    def __init__(self, config: EnhancedSearchConfig):
        """Initialize fusion engine.

        Args:
            config: Search configuration
        """
        self.config = config
        self.logger = LoggingConfig.get_logger(__name__)

    def normalize_scores(
        self, results: list[EnhancedSearchResult], score_field: str = "combined_score"
    ) -> list[EnhancedSearchResult]:
        """Normalize scores to 0-1 range using min-max normalization.

        Args:
            results: List of search results to normalize
            score_field: Field name containing the score to normalize

        Returns:
            Results with normalized scores
        """
        if not results:
            return results

        try:
            scores = [getattr(result, score_field) for result in results]
            min_score = min(scores)
            max_score = max(scores)

            # Avoid division by zero
            if max_score == min_score:
                for result in results:
                    setattr(result, score_field, 1.0)
            else:
                score_range = max_score - min_score
                for result in results:
                    current_score = getattr(result, score_field)
                    normalized_score = (current_score - min_score) / score_range
                    setattr(result, score_field, normalized_score)

            return results

        except Exception as e:
            self.logger.warning(f"Score normalization failed: {e}")
            return results

    def apply_score_boosting(
        self, results: list[EnhancedSearchResult]
    ) -> list[EnhancedSearchResult]:
        """Apply score boosting based on result characteristics.

        Args:
            results: List of search results

        Returns:
            Results with boosted scores
        """
        try:
            for result in results:
                boost_factor = 1.0

                # Boost based on centrality score (for graph results)
                if result.centrality_score > 0:
                    boost_factor += 0.1 * result.centrality_score

                # Boost based on temporal relevance
                if result.temporal_relevance > 0:
                    boost_factor += 0.05 * result.temporal_relevance

                # Boost based on entity count (more entities = more connected)
                if result.entity_ids:
                    entity_boost = min(0.2, len(result.entity_ids) * 0.02)
                    boost_factor += entity_boost

                # Boost based on relationship diversity
                if result.relationship_types:
                    relationship_boost = min(
                        0.15, len(set(result.relationship_types)) * 0.03
                    )
                    boost_factor += relationship_boost

                # Apply boost to combined score
                result.combined_score *= boost_factor

                # Store boost information in debug info
                result.debug_info["boost_factor"] = boost_factor

            return results

        except Exception as e:
            self.logger.warning(f"Score boosting failed: {e}")
            return results

    def select_optimal_fusion_strategy(
        self,
        query: str,
        vector_results: list[EnhancedSearchResult],
        keyword_results: list[EnhancedSearchResult],
        graph_results: list[EnhancedSearchResult],
    ) -> FusionStrategy:
        """Select the optimal fusion strategy based on query and result characteristics.

        Args:
            query: Search query text
            vector_results: Results from vector search
            keyword_results: Results from keyword search
            graph_results: Results from graph search

        Returns:
            Recommended fusion strategy
        """
        try:
            # Analyze query characteristics
            query_tokens = query.lower().split()
            query_length = len(query_tokens)

            # Count results from each source
            vector_count = len(vector_results)
            keyword_count = len(keyword_results)
            graph_count = len(graph_results)
            total_results = vector_count + keyword_count + graph_count

            # Calculate result quality metrics
            avg_vector_score = (
                sum(r.vector_score for r in vector_results) / vector_count
                if vector_count > 0
                else 0
            )
            avg_keyword_score = (
                sum(r.keyword_score for r in keyword_results) / keyword_count
                if keyword_count > 0
                else 0
            )
            avg_graph_score = (
                sum(r.graph_score for r in graph_results) / graph_count
                if graph_count > 0
                else 0
            )

            # Calculate result diversity (unique content)
            all_results = vector_results + keyword_results + graph_results
            unique_content = set()
            for result in all_results:
                content_hash = hashlib.md5(result.content.encode()).hexdigest()
                unique_content.add(content_hash)

            diversity_ratio = (
                len(unique_content) / len(all_results) if all_results else 0
            )

            # Calculate graph richness (centrality and relationships)
            graph_richness = 0.0
            if graph_results:
                total_centrality = sum(r.centrality_score for r in graph_results)
                total_entities = sum(len(r.entity_ids) for r in graph_results)
                total_relationships = sum(
                    len(r.relationship_types) for r in graph_results
                )
                graph_richness = (
                    total_centrality + total_entities * 0.1 + total_relationships * 0.05
                ) / graph_count

            # Enhanced decision logic for fusion strategy selection

            # Context-aware fusion for complex scenarios with mixed quality
            if (
                total_results > 15
                and abs(avg_vector_score - avg_graph_score) < 0.3
                and diversity_ratio > 0.6
            ):
                self.logger.debug(
                    "Selected context-aware fusion due to complex mixed-quality scenario"
                )
                return FusionStrategy.CONTEXT_AWARE

            # Graph-enhanced weighted for high-quality graph results
            if graph_count > 5 and avg_graph_score > 0.6 and graph_richness > 0.5:
                self.logger.debug(
                    "Selected graph-enhanced weighted fusion due to high-quality graph results"
                )
                return FusionStrategy.GRAPH_ENHANCED_WEIGHTED

            # Multi-stage fusion for large result sets that need refinement
            if total_results > 25:
                self.logger.debug("Selected multi-stage fusion due to large result set")
                return FusionStrategy.MULTI_STAGE

            # Confidence adaptive for unbalanced result quality
            if (
                max(avg_vector_score, avg_keyword_score, avg_graph_score)
                - min(avg_vector_score, avg_keyword_score, avg_graph_score)
                > 0.4
            ):
                self.logger.debug(
                    "Selected confidence adaptive fusion due to unbalanced result quality"
                )
                return FusionStrategy.CONFIDENCE_ADAPTIVE

            # MMR for diverse results or when we want to avoid redundancy
            if diversity_ratio < 0.7 and len(all_results) > 10:
                self.logger.debug("Selected MMR fusion due to low diversity")
                return FusionStrategy.MMR

            # RRF when we have balanced results from multiple sources
            if (
                vector_count > 5
                and keyword_count > 5
                and graph_count > 5
                and abs(vector_count - keyword_count) < 10
                and abs(vector_count - graph_count) < 10
            ):
                self.logger.debug(
                    "Selected RRF fusion due to balanced multi-source results"
                )
                return FusionStrategy.RECIPROCAL_RANK_FUSION

            # Weighted sum for simple queries or when one source dominates
            if query_length <= 3 or max(
                vector_count, keyword_count, graph_count
            ) > 2 * min(vector_count, keyword_count, graph_count):
                self.logger.debug(
                    "Selected weighted sum fusion for simple query or dominant source"
                )
                return FusionStrategy.WEIGHTED_SUM

            # Default to graph-enhanced weighted for general cases
            self.logger.debug(
                "Selected graph-enhanced weighted fusion as enhanced default"
            )
            return FusionStrategy.GRAPH_ENHANCED_WEIGHTED

        except Exception as e:
            self.logger.warning(f"Fusion strategy selection failed: {e}")
            return FusionStrategy.GRAPH_ENHANCED_WEIGHTED  # Enhanced default

    def fuse_results(
        self,
        vector_results: list[EnhancedSearchResult],
        keyword_results: list[EnhancedSearchResult],
        graph_results: list[EnhancedSearchResult],
        query_weights: QueryWeights | None = None,
    ) -> list[EnhancedSearchResult]:
        """Fuse results from vector, keyword, and graph search.

        Args:
            vector_results: Results from vector search
            keyword_results: Results from keyword search
            graph_results: Results from graph search
            query_weights: Optional query-time weight overrides

        Returns:
            Fused and ranked results
        """
        try:
            # Normalize scores within each result type for fair comparison
            vector_results = self.normalize_scores(vector_results, "vector_score")
            keyword_results = self.normalize_scores(keyword_results, "keyword_score")
            graph_results = self.normalize_scores(graph_results, "graph_score")

            # Apply fusion strategy
            if self.config.fusion_strategy == FusionStrategy.WEIGHTED_SUM:
                fused_results = self._weighted_sum_fusion(
                    vector_results, keyword_results, graph_results, query_weights
                )
            elif self.config.fusion_strategy == FusionStrategy.RECIPROCAL_RANK_FUSION:
                fused_results = self._reciprocal_rank_fusion(
                    vector_results, keyword_results, graph_results, query_weights
                )
            elif self.config.fusion_strategy == FusionStrategy.MMR:
                fused_results = self._mmr_fusion(
                    vector_results,
                    keyword_results,
                    graph_results,
                    query_weights=query_weights,
                )
            elif self.config.fusion_strategy == FusionStrategy.GRAPH_ENHANCED_WEIGHTED:
                fused_results = self._graph_enhanced_weighted_fusion(
                    vector_results, keyword_results, graph_results, query_weights
                )
            elif self.config.fusion_strategy == FusionStrategy.CONFIDENCE_ADAPTIVE:
                fused_results = self._confidence_adaptive_fusion(
                    vector_results, keyword_results, graph_results, query_weights
                )
            elif self.config.fusion_strategy == FusionStrategy.MULTI_STAGE:
                fused_results = self._multi_stage_fusion(
                    vector_results, keyword_results, graph_results, query_weights
                )
            elif self.config.fusion_strategy == FusionStrategy.CONTEXT_AWARE:
                fused_results = self._context_aware_fusion(
                    vector_results, keyword_results, graph_results, query_weights
                )
            else:
                # Default to weighted sum
                fused_results = self._weighted_sum_fusion(
                    vector_results, keyword_results, graph_results, query_weights
                )

            # Apply score boosting based on result characteristics
            fused_results = self.apply_score_boosting(fused_results)

            # Final normalization of combined scores - but preserve relative ordering
            # and ensure no scores become exactly 0 unless they were originally 0
            if len(fused_results) > 1:
                # Store original scores to detect if any were originally > 0
                original_scores = [r.combined_score for r in fused_results]
                min_original = min(original_scores)

                # Apply normalization
                fused_results = self.normalize_scores(fused_results, "combined_score")

                # If normalization created zeros from non-zero scores, adjust
                if min_original > 0:
                    for result in fused_results:
                        if result.combined_score == 0.0:
                            result.combined_score = 0.001  # Small non-zero value
            elif len(fused_results) == 1:
                # Single result gets score 1.0
                fused_results[0].combined_score = 1.0

            # Sort by final combined score
            fused_results.sort(key=lambda x: x.combined_score, reverse=True)

            # Add fusion strategy information to debug info
            for result in fused_results:
                result.debug_info["fusion_strategy"] = self.config.fusion_strategy.value
                result.debug_info["weights"] = {
                    "vector": self.config.vector_weight,
                    "keyword": self.config.keyword_weight,
                    "graph": self.config.graph_weight,
                }

            return fused_results[: self.config.final_limit]

        except Exception as e:
            self.logger.error(f"Result fusion failed: {e}")
            # Return vector results as fallback
            return vector_results[: self.config.final_limit]

    def _weighted_sum_fusion(
        self,
        vector_results: list[EnhancedSearchResult],
        keyword_results: list[EnhancedSearchResult],
        graph_results: list[EnhancedSearchResult],
        query_weights: QueryWeights | None = None,
    ) -> list[EnhancedSearchResult]:
        """Fuse results using weighted sum of scores."""
        # Create a mapping of content to results
        result_map = {}

        # Add vector results
        for result in vector_results:
            key = self._get_result_key(result)
            if key not in result_map:
                result_map[key] = result
            else:
                # Update existing result with vector score
                result_map[key].vector_score = max(
                    result_map[key].vector_score, result.vector_score
                )

        # Add keyword results
        for result in keyword_results:
            key = self._get_result_key(result)
            if key not in result_map:
                result_map[key] = result
            else:
                # Update existing result with keyword score
                result_map[key].keyword_score = max(
                    result_map[key].keyword_score, result.keyword_score
                )

        # Add graph results
        for result in graph_results:
            key = self._get_result_key(result)
            if key not in result_map:
                result_map[key] = result
            else:
                # Update existing result with graph score
                result_map[key].graph_score = max(
                    result_map[key].graph_score, result.graph_score
                )
                # Merge graph-specific information
                result_map[key].entity_ids.extend(result.entity_ids)
                result_map[key].relationship_types.extend(result.relationship_types)
                result_map[key].centrality_score = max(
                    result_map[key].centrality_score, result.centrality_score
                )

        # Get effective weights (query-time overrides or config defaults)
        if query_weights and query_weights.has_weights():
            vector_weight, keyword_weight, graph_weight = (
                query_weights.get_effective_weights(self.config)
            )
        else:
            vector_weight, keyword_weight, graph_weight = (
                self.config.vector_weight,
                self.config.keyword_weight,
                self.config.graph_weight,
            )

        # Calculate combined scores
        fused_results = []
        for result in result_map.values():
            combined_score = (
                vector_weight * result.vector_score
                + keyword_weight * result.keyword_score
                + graph_weight * result.graph_score
            )

            # Ensure minimum positive score if any component score is > 0
            if (
                result.vector_score > 0
                or result.keyword_score > 0
                or result.graph_score > 0
            ):
                combined_score = max(combined_score, 0.001)

            if combined_score >= self.config.min_combined_score:
                result.combined_score = combined_score
                fused_results.append(result)

        # Sort by combined score
        fused_results.sort(key=lambda x: x.combined_score, reverse=True)
        return fused_results[: self.config.final_limit]

    def _reciprocal_rank_fusion(
        self,
        vector_results: list[EnhancedSearchResult],
        keyword_results: list[EnhancedSearchResult],
        graph_results: list[EnhancedSearchResult],
        query_weights: QueryWeights | None = None,
    ) -> list[EnhancedSearchResult]:
        """Fuse results using reciprocal rank fusion (RRF)."""
        # Create rank mappings for each result type
        vector_ranks = {
            self._get_result_key(r): i + 1 for i, r in enumerate(vector_results)
        }
        keyword_ranks = {
            self._get_result_key(r): i + 1 for i, r in enumerate(keyword_results)
        }
        graph_ranks = {
            self._get_result_key(r): i + 1 for i, r in enumerate(graph_results)
        }

        # Collect all unique results
        all_results = {}
        for results in [vector_results, keyword_results, graph_results]:
            for result in results:
                key = self._get_result_key(result)
                if key not in all_results:
                    all_results[key] = result

        # Get effective weights (query-time overrides or config defaults)
        if query_weights and query_weights.has_weights():
            vector_weight, keyword_weight, graph_weight = (
                query_weights.get_effective_weights(self.config)
            )
        else:
            vector_weight, keyword_weight, graph_weight = (
                self.config.vector_weight,
                self.config.keyword_weight,
                self.config.graph_weight,
            )

        # Calculate RRF scores
        k = 60  # RRF constant
        for key, result in all_results.items():
            rrf_score = 0.0

            if key in vector_ranks:
                rrf_score += vector_weight / (k + vector_ranks[key])
            if key in keyword_ranks:
                rrf_score += keyword_weight / (k + keyword_ranks[key])
            if key in graph_ranks:
                rrf_score += graph_weight / (k + graph_ranks[key])

            # Ensure minimum positive score
            result.combined_score = max(rrf_score, 0.001)

        # Filter by minimum score threshold
        filtered_results = [
            result
            for result in all_results.values()
            if result.combined_score >= self.config.min_combined_score
        ]

        # Sort by RRF score and return top results
        filtered_results.sort(key=lambda x: x.combined_score, reverse=True)
        return filtered_results[: self.config.final_limit]

    def _mmr_fusion(
        self,
        vector_results: list[EnhancedSearchResult],
        keyword_results: list[EnhancedSearchResult],
        graph_results: list[EnhancedSearchResult],
        lambda_param: float = 0.7,
        query_weights: QueryWeights | None = None,
    ) -> list[EnhancedSearchResult]:
        """Fuse results using Maximal Marginal Relevance (MMR).

        MMR balances relevance and diversity by selecting results that are
        relevant to the query but dissimilar to already selected results.

        Args:
            vector_results: Results from vector search
            keyword_results: Results from keyword search
            graph_results: Results from graph search
            lambda_param: Trade-off parameter between relevance and diversity (0-1)
                         1.0 = pure relevance, 0.0 = pure diversity

        Returns:
            Diversified and relevant results
        """
        try:
            # Combine all results and calculate initial relevance scores
            all_results = self._combine_and_score_results(
                vector_results, keyword_results, graph_results, query_weights
            )

            if not all_results:
                return []

            # Sort by relevance score initially
            all_results.sort(key=lambda x: x.combined_score, reverse=True)

            # MMR selection algorithm
            selected_results = []
            remaining_results = all_results.copy()

            # Select the most relevant result first
            if remaining_results:
                best_result = remaining_results.pop(0)
                selected_results.append(best_result)

            # Iteratively select results that maximize MMR score
            while remaining_results and len(selected_results) < self.config.final_limit:
                best_mmr_score = -float("inf")
                best_result_idx = 0

                for i, candidate in enumerate(remaining_results):
                    # Calculate relevance score (normalized)
                    relevance_score = candidate.combined_score

                    # Calculate maximum similarity to already selected results
                    max_similarity = 0.0
                    if selected_results:
                        similarities = [
                            self._calculate_content_similarity(candidate, selected)
                            for selected in selected_results
                        ]
                        max_similarity = max(similarities)

                    # Calculate MMR score
                    mmr_score = (
                        lambda_param * relevance_score
                        - (1 - lambda_param) * max_similarity
                    )

                    if mmr_score > best_mmr_score:
                        best_mmr_score = mmr_score
                        best_result_idx = i

                # Select the best MMR result
                selected_result = remaining_results.pop(best_result_idx)
                selected_result.combined_score = best_mmr_score
                selected_results.append(selected_result)

            return selected_results

        except Exception as e:
            self.logger.warning(f"MMR fusion failed: {e}")
            # Fallback to weighted sum
            return self._weighted_sum_fusion(
                vector_results, keyword_results, graph_results, query_weights
            )

    def _graph_enhanced_weighted_fusion(
        self,
        vector_results: list[EnhancedSearchResult],
        keyword_results: list[EnhancedSearchResult],
        graph_results: list[EnhancedSearchResult],
        query_weights: QueryWeights | None = None,
    ) -> list[EnhancedSearchResult]:
        """Enhanced weighted fusion that leverages graph centrality and temporal factors.

        This fusion strategy applies sophisticated graph-based boosting to improve
        the integration of vector similarity and graph relationship scores.
        """
        try:
            # Start with basic weighted sum fusion
            result_map = {}

            # Get effective weights
            if query_weights and query_weights.has_weights():
                vector_weight, keyword_weight, graph_weight = (
                    query_weights.get_effective_weights(self.config)
                )
            else:
                vector_weight, keyword_weight, graph_weight = (
                    self.config.vector_weight,
                    self.config.keyword_weight,
                    self.config.graph_weight,
                )

            # Process and combine all results
            for results, weight, score_field in [
                (vector_results, vector_weight, "vector_score"),
                (keyword_results, keyword_weight, "keyword_score"),
                (graph_results, graph_weight, "graph_score"),
            ]:
                for result in results:
                    key = self._get_result_key(result)
                    if key not in result_map:
                        result_map[key] = result
                        result_map[key].combined_score = weight * getattr(
                            result, score_field
                        )
                    else:
                        # Merge results and update scores
                        existing = result_map[key]
                        setattr(
                            existing,
                            score_field,
                            max(
                                getattr(existing, score_field),
                                getattr(result, score_field),
                            ),
                        )
                        existing.combined_score += weight * getattr(result, score_field)

                        # Merge graph-specific information
                        if hasattr(result, "entity_ids") and result.entity_ids:
                            existing.entity_ids.extend(result.entity_ids)
                        if (
                            hasattr(result, "relationship_types")
                            and result.relationship_types
                        ):
                            existing.relationship_types.extend(
                                result.relationship_types
                            )
                        if hasattr(result, "centrality_score"):
                            existing.centrality_score = max(
                                existing.centrality_score, result.centrality_score
                            )

            # Apply graph-enhanced scoring
            for result in result_map.values():
                # Graph centrality boost (exponential scaling for high centrality)
                if result.centrality_score > 0:
                    centrality_boost = 1.0 + (result.centrality_score**1.5) * 0.3
                    result.combined_score *= centrality_boost
                    result.debug_info["centrality_boost"] = centrality_boost

                # Temporal relevance boost (recent content gets higher boost)
                if result.temporal_relevance > 0:
                    temporal_boost = 1.0 + (result.temporal_relevance**0.8) * 0.2
                    result.combined_score *= temporal_boost
                    result.debug_info["temporal_boost"] = temporal_boost

                # Entity connectivity boost (more connected entities = higher relevance)
                if result.entity_ids:
                    unique_entities = len(set(result.entity_ids))
                    connectivity_boost = 1.0 + min(0.25, unique_entities * 0.03)
                    result.combined_score *= connectivity_boost
                    result.debug_info["connectivity_boost"] = connectivity_boost

                # Relationship diversity boost
                if result.relationship_types:
                    unique_relationships = len(set(result.relationship_types))
                    diversity_boost = 1.0 + min(0.2, unique_relationships * 0.04)
                    result.combined_score *= diversity_boost
                    result.debug_info["diversity_boost"] = diversity_boost

            # Filter and sort results
            filtered_results = [
                result
                for result in result_map.values()
                if result.combined_score >= self.config.min_combined_score
            ]

            filtered_results.sort(key=lambda x: x.combined_score, reverse=True)
            return filtered_results[: self.config.final_limit]

        except Exception as e:
            self.logger.warning(f"Graph enhanced weighted fusion failed: {e}")
            return self._weighted_sum_fusion(
                vector_results, keyword_results, graph_results, query_weights
            )

    def _confidence_adaptive_fusion(
        self,
        vector_results: list[EnhancedSearchResult],
        keyword_results: list[EnhancedSearchResult],
        graph_results: list[EnhancedSearchResult],
        query_weights: QueryWeights | None = None,
    ) -> list[EnhancedSearchResult]:
        """Adaptive fusion that adjusts weights based on result confidence scores.

        This strategy dynamically adjusts the fusion weights based on the confidence
        and quality of results from each search modality.
        """
        try:
            # Calculate confidence scores for each result type
            vector_confidence = self._calculate_result_confidence(
                vector_results, "vector"
            )
            keyword_confidence = self._calculate_result_confidence(
                keyword_results, "keyword"
            )
            graph_confidence = self._calculate_result_confidence(graph_results, "graph")

            # Get base weights
            if query_weights and query_weights.has_weights():
                base_vector_weight, base_keyword_weight, base_graph_weight = (
                    query_weights.get_effective_weights(self.config)
                )
            else:
                base_vector_weight, base_keyword_weight, base_graph_weight = (
                    self.config.vector_weight,
                    self.config.keyword_weight,
                    self.config.graph_weight,
                )

            # Adjust weights based on confidence
            total_confidence = vector_confidence + keyword_confidence + graph_confidence
            if total_confidence > 0:
                confidence_factor = 0.3  # How much confidence affects weighting

                vector_weight = base_vector_weight * (
                    1
                    + confidence_factor * (vector_confidence / total_confidence - 1 / 3)
                )
                keyword_weight = base_keyword_weight * (
                    1
                    + confidence_factor
                    * (keyword_confidence / total_confidence - 1 / 3)
                )
                graph_weight = base_graph_weight * (
                    1
                    + confidence_factor * (graph_confidence / total_confidence - 1 / 3)
                )

                # Normalize weights to sum to 1.0
                total_weight = vector_weight + keyword_weight + graph_weight
                if total_weight > 0:
                    vector_weight /= total_weight
                    keyword_weight /= total_weight
                    graph_weight /= total_weight
            else:
                vector_weight, keyword_weight, graph_weight = (
                    base_vector_weight,
                    base_keyword_weight,
                    base_graph_weight,
                )

            # Create adjusted query weights
            adjusted_weights = QueryWeights(
                vector_weight=vector_weight,
                keyword_weight=keyword_weight,
                graph_weight=graph_weight,
            )

            # Use graph enhanced weighted fusion with adjusted weights
            results = self._graph_enhanced_weighted_fusion(
                vector_results, keyword_results, graph_results, adjusted_weights
            )

            # Add confidence information to debug info
            for result in results:
                result.debug_info.update(
                    {
                        "vector_confidence": vector_confidence,
                        "keyword_confidence": keyword_confidence,
                        "graph_confidence": graph_confidence,
                        "adjusted_vector_weight": vector_weight,
                        "adjusted_keyword_weight": keyword_weight,
                        "adjusted_graph_weight": graph_weight,
                    }
                )

            return results

        except Exception as e:
            self.logger.warning(f"Confidence adaptive fusion failed: {e}")
            return self._graph_enhanced_weighted_fusion(
                vector_results, keyword_results, graph_results, query_weights
            )

    def _multi_stage_fusion(
        self,
        vector_results: list[EnhancedSearchResult],
        keyword_results: list[EnhancedSearchResult],
        graph_results: list[EnhancedSearchResult],
        query_weights: QueryWeights | None = None,
    ) -> list[EnhancedSearchResult]:
        """Multi-stage fusion with preliminary filtering and progressive refinement.

        This strategy applies fusion in multiple stages:
        1. Initial filtering based on individual scores
        2. Primary fusion with basic weighting
        3. Refinement with graph enhancement
        4. Final reranking with confidence adjustment
        """
        try:
            # Stage 1: Initial filtering - remove low-quality results
            filtered_vector = [
                r
                for r in vector_results
                if r.vector_score >= self.config.min_vector_score
            ]
            filtered_keyword = [
                r for r in keyword_results if r.keyword_score >= 0.1
            ]  # Lower threshold for keyword
            filtered_graph = [
                r for r in graph_results if r.graph_score >= self.config.min_graph_score
            ]

            self.logger.debug(
                f"Stage 1 filtering: vector {len(vector_results)}->{len(filtered_vector)}, "
                f"keyword {len(keyword_results)}->{len(filtered_keyword)}, "
                f"graph {len(graph_results)}->{len(filtered_graph)}"
            )

            # Stage 2: Primary fusion with weighted sum
            stage2_results = self._weighted_sum_fusion(
                filtered_vector, filtered_keyword, filtered_graph, query_weights
            )

            # Stage 3: Graph enhancement for top candidates
            top_k = min(
                self.config.final_limit * 2, len(stage2_results)
            )  # Process 2x final limit
            stage3_candidates = stage2_results[:top_k]

            # Apply graph enhancement to top candidates
            for result in stage3_candidates:
                enhancement_factor = 1.0

                # Enhanced centrality scoring
                if result.centrality_score > 0:
                    enhancement_factor += result.centrality_score * 0.4

                # Enhanced temporal scoring
                if result.temporal_relevance > 0:
                    enhancement_factor += result.temporal_relevance * 0.3

                # Multi-modal presence bonus (appears in multiple search types)
                modality_count = sum(
                    [
                        1 if result.vector_score > 0 else 0,
                        1 if result.keyword_score > 0 else 0,
                        1 if result.graph_score > 0 else 0,
                    ]
                )
                if modality_count > 1:
                    enhancement_factor += (modality_count - 1) * 0.15

                result.combined_score *= enhancement_factor
                result.debug_info["stage3_enhancement"] = enhancement_factor

            # Stage 4: Final confidence-based reranking
            stage4_results = sorted(
                stage3_candidates, key=lambda x: x.combined_score, reverse=True
            )

            # Apply final confidence adjustment
            for i, result in enumerate(stage4_results):
                # Position-based confidence (earlier results get slight boost)
                position_factor = 1.0 + (
                    0.1 * (len(stage4_results) - i) / len(stage4_results)
                )
                result.combined_score *= position_factor
                result.debug_info["position_factor"] = position_factor

            # Final sort and limit
            final_results = sorted(
                stage4_results, key=lambda x: x.combined_score, reverse=True
            )
            return final_results[: self.config.final_limit]

        except Exception as e:
            self.logger.warning(f"Multi-stage fusion failed: {e}")
            return self._confidence_adaptive_fusion(
                vector_results, keyword_results, graph_results, query_weights
            )

    def _context_aware_fusion(
        self,
        vector_results: list[EnhancedSearchResult],
        keyword_results: list[EnhancedSearchResult],
        graph_results: list[EnhancedSearchResult],
        query_weights: QueryWeights | None = None,
    ) -> list[EnhancedSearchResult]:
        """Context-aware fusion that adapts based on query characteristics and result patterns.

        This strategy analyzes the query and result characteristics to select
        the most appropriate fusion approach dynamically.
        """
        try:
            # Analyze result characteristics
            total_results = (
                len(vector_results) + len(keyword_results) + len(graph_results)
            )
            vector_ratio = (
                len(vector_results) / total_results if total_results > 0 else 0
            )
            keyword_ratio = (
                len(keyword_results) / total_results if total_results > 0 else 0
            )
            graph_ratio = len(graph_results) / total_results if total_results > 0 else 0

            # Calculate average scores for each modality
            avg_vector_score = (
                sum(r.vector_score for r in vector_results) / len(vector_results)
                if vector_results
                else 0
            )
            avg_keyword_score = (
                sum(r.keyword_score for r in keyword_results) / len(keyword_results)
                if keyword_results
                else 0
            )
            avg_graph_score = (
                sum(r.graph_score for r in graph_results) / len(graph_results)
                if graph_results
                else 0
            )

            # Determine context-based strategy
            if graph_ratio > 0.4 and avg_graph_score > 0.6:
                # High-quality graph results available - use graph-enhanced fusion
                self.logger.debug(
                    "Context-aware: Using graph-enhanced fusion (high graph quality)"
                )
                return self._graph_enhanced_weighted_fusion(
                    vector_results, keyword_results, graph_results, query_weights
                )

            elif vector_ratio > 0.6 and avg_vector_score > 0.7:
                # Strong vector results - use confidence adaptive
                self.logger.debug(
                    "Context-aware: Using confidence adaptive fusion (strong vector results)"
                )
                return self._confidence_adaptive_fusion(
                    vector_results, keyword_results, graph_results, query_weights
                )

            elif total_results > 20:
                # Many results available - use multi-stage for refinement
                self.logger.debug(
                    "Context-aware: Using multi-stage fusion (many results)"
                )
                return self._multi_stage_fusion(
                    vector_results, keyword_results, graph_results, query_weights
                )

            elif keyword_ratio > 0.5:
                # Keyword-heavy results - use MMR for diversity
                self.logger.debug("Context-aware: Using MMR fusion (keyword-heavy)")
                return self._mmr_fusion(
                    vector_results,
                    keyword_results,
                    graph_results,
                    query_weights=query_weights,
                )

            else:
                # Balanced or uncertain - use RRF as safe default
                self.logger.debug("Context-aware: Using RRF fusion (balanced/default)")
                return self._reciprocal_rank_fusion(
                    vector_results, keyword_results, graph_results, query_weights
                )

        except Exception as e:
            self.logger.warning(f"Context-aware fusion failed: {e}")
            return self._multi_stage_fusion(
                vector_results, keyword_results, graph_results, query_weights
            )

    def _calculate_result_confidence(
        self, results: list[EnhancedSearchResult], result_type: str
    ) -> float:
        """Calculate confidence score for a set of results.

        Args:
            results: List of search results
            result_type: Type of results ("vector", "keyword", or "graph")

        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not results:
            return 0.0

        try:
            # Get relevant scores based on result type
            if result_type == "vector":
                scores = [r.vector_score for r in results]
            elif result_type == "keyword":
                scores = [r.keyword_score for r in results]
            elif result_type == "graph":
                scores = [r.graph_score for r in results]
            else:
                scores = [r.combined_score for r in results]

            if not scores:
                return 0.0

            # Calculate confidence metrics
            avg_score = sum(scores) / len(scores)
            max_score = max(scores)
            score_variance = sum((s - avg_score) ** 2 for s in scores) / len(scores)
            score_std = score_variance**0.5

            # Confidence factors
            quality_factor = min(
                1.0, avg_score * 2
            )  # Higher average = higher confidence
            consistency_factor = max(
                0.0, 1.0 - score_std
            )  # Lower variance = higher confidence
            peak_factor = min(
                1.0, max_score * 1.5
            )  # High peak score = higher confidence
            volume_factor = min(
                1.0, len(results) / 10
            )  # More results = higher confidence (up to 10)

            # Weighted combination
            confidence = (
                0.4 * quality_factor
                + 0.2 * consistency_factor
                + 0.3 * peak_factor
                + 0.1 * volume_factor
            )

            return min(1.0, max(0.0, confidence))

        except Exception as e:
            self.logger.warning(f"Error calculating confidence for {result_type}: {e}")
            return 0.5  # Neutral confidence on error

    def _combine_and_score_results(
        self,
        vector_results: list[EnhancedSearchResult],
        keyword_results: list[EnhancedSearchResult],
        graph_results: list[EnhancedSearchResult],
        query_weights: QueryWeights | None = None,
    ) -> list[EnhancedSearchResult]:
        """Combine results from all sources and calculate initial relevance scores."""
        # Get effective weights (query-time overrides or config defaults)
        if query_weights and query_weights.has_weights():
            vector_weight, keyword_weight, graph_weight = (
                query_weights.get_effective_weights(self.config)
            )
        else:
            vector_weight, keyword_weight, graph_weight = (
                self.config.vector_weight,
                self.config.keyword_weight,
                self.config.graph_weight,
            )

        result_map = {}

        # Process vector results
        for result in vector_results:
            key = self._get_result_key(result)
            if key not in result_map:
                result_map[key] = result
                result_map[key].combined_score = vector_weight * result.vector_score
            else:
                result_map[key].vector_score = max(
                    result_map[key].vector_score, result.vector_score
                )
                result_map[key].combined_score += vector_weight * result.vector_score

        # Process keyword results
        for result in keyword_results:
            key = self._get_result_key(result)
            if key not in result_map:
                result_map[key] = result
                result_map[key].combined_score = keyword_weight * result.keyword_score
            else:
                result_map[key].keyword_score = max(
                    result_map[key].keyword_score, result.keyword_score
                )
                result_map[key].combined_score += keyword_weight * result.keyword_score

        # Process graph results
        for result in graph_results:
            key = self._get_result_key(result)
            if key not in result_map:
                result_map[key] = result
                result_map[key].combined_score = graph_weight * result.graph_score
            else:
                result_map[key].graph_score = max(
                    result_map[key].graph_score, result.graph_score
                )
                result_map[key].combined_score += graph_weight * result.graph_score
                # Merge graph-specific metadata
                result_map[key].entity_ids.extend(result.entity_ids)
                result_map[key].relationship_types.extend(result.relationship_types)
                result_map[key].centrality_score = max(
                    result_map[key].centrality_score, result.centrality_score
                )

        # Filter by minimum score threshold
        filtered_results = [
            result
            for result in result_map.values()
            if result.combined_score >= self.config.min_combined_score
        ]

        return filtered_results

    def _calculate_content_similarity(
        self, result1: EnhancedSearchResult, result2: EnhancedSearchResult
    ) -> float:
        """Calculate similarity between two search results.

        Uses a combination of content similarity and metadata overlap.

        Args:
            result1: First search result
            result2: Second search result

        Returns:
            Similarity score between 0.0 and 1.0
        """
        try:
            # Content similarity using simple token overlap (Jaccard similarity)
            content1_tokens = set(result1.content.lower().split())
            content2_tokens = set(result2.content.lower().split())

            if not content1_tokens and not content2_tokens:
                content_similarity = 1.0
            elif not content1_tokens or not content2_tokens:
                content_similarity = 0.0
            else:
                intersection = len(content1_tokens.intersection(content2_tokens))
                union = len(content1_tokens.union(content2_tokens))
                content_similarity = intersection / union if union > 0 else 0.0

            # Title similarity
            title1_tokens = set(result1.title.lower().split())
            title2_tokens = set(result2.title.lower().split())

            if not title1_tokens and not title2_tokens:
                title_similarity = 1.0
            elif not title1_tokens or not title2_tokens:
                title_similarity = 0.0
            else:
                intersection = len(title1_tokens.intersection(title2_tokens))
                union = len(title1_tokens.union(title2_tokens))
                title_similarity = intersection / union if union > 0 else 0.0

            # Source type similarity
            source_similarity = (
                1.0 if result1.source_type == result2.source_type else 0.0
            )

            # Entity overlap similarity (for graph results)
            entity1_set = set(result1.entity_ids)
            entity2_set = set(result2.entity_ids)

            if not entity1_set and not entity2_set:
                entity_similarity = 0.0  # No entities to compare
            elif not entity1_set or not entity2_set:
                entity_similarity = 0.0
            else:
                intersection = len(entity1_set.intersection(entity2_set))
                union = len(entity1_set.union(entity2_set))
                entity_similarity = intersection / union if union > 0 else 0.0

            # Weighted combination of similarities
            overall_similarity = (
                0.5 * content_similarity
                + 0.2 * title_similarity
                + 0.1 * source_similarity
                + 0.2 * entity_similarity
            )

            return min(1.0, max(0.0, overall_similarity))

        except Exception as e:
            self.logger.warning(f"Error calculating content similarity: {e}")
            return 0.0

    def _get_result_key(self, result: EnhancedSearchResult) -> str:
        """Generate a key for result deduplication."""
        # Use content hash for deduplication
        content_hash = hashlib.md5(result.content.encode()).hexdigest()
        return f"{result.source_type}_{content_hash}"
