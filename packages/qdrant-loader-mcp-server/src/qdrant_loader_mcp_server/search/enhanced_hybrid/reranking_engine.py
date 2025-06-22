import asyncio
from datetime import datetime
from typing import Any, cast

from openai import AsyncOpenAI
from openai.types.completion import Completion

from ...utils.logging import LoggingConfig
from .models import EnhancedSearchConfig, EnhancedSearchResult, RerankingStrategy


class RerankingEngine:
    """Reranking engine for search results."""

    def __init__(
        self, config: EnhancedSearchConfig, openai_client: AsyncOpenAI | None = None
    ):
        """Initialize reranking engine.

        Args:
            config: Enhanced search configuration
            openai_client: AsyncOpenAI client (optional)
        """
        self.config = config
        self.openai_client = openai_client
        self.bge_reranker = None
        self.logger = LoggingConfig.get_logger(__name__)

        if (
            self.config.reranking_strategy == RerankingStrategy.CROSS_ENCODER
            or self.config.reranking_strategy == RerankingStrategy.COMBINED
        ) and self.config.cross_encoder_model == "bge":
            self._initialize_bge_reranker()

    def _initialize_bge_reranker(self):
        """Initialize BGE reranker model."""
        try:
            from FlagEmbedding import BGEM3Reranker  # type: ignore

            self.bge_reranker = BGEM3Reranker()
            self.logger.info("BGE-M3 Reranker initialized successfully.")
        except ImportError:
            self.logger.warning(
                "FlagEmbedding library not found. "
                "BGE reranking will not be available. "
                "Install with: pip install FlagEmbedding"
            )
            self.bge_reranker = None
        except Exception as e:
            self.logger.error(f"Failed to initialize BGE reranker: {e}")
            self.bge_reranker = None

    async def rerank_results(
        self,
        query: str,
        results: list[EnhancedSearchResult],
        user_context: dict[str, Any] | None = None,
    ) -> list[EnhancedSearchResult]:
        """Rerank search results using the configured strategy.

        Args:
            query: Search query
            results: List of search results to rerank
            user_context: User context for contextual reranking

        Returns:
            Reranked list of search results
        """
        if not self.config.enable_reranking or self.config.reranking_strategy in [
            RerankingStrategy.NONE,
            None,
        ]:
            return results

        top_k_results = results[: self.config.rerank_top_k]

        strategy_map = {
            RerankingStrategy.CROSS_ENCODER: self._cross_encoder_rerank,
            RerankingStrategy.DIVERSITY_MMR: self._diversity_rerank,
            RerankingStrategy.TEMPORAL_BOOST: self._temporal_rerank,
            RerankingStrategy.CONTEXTUAL_BOOST: self._contextual_rerank,
            RerankingStrategy.COMBINED: self._combined_rerank,
        }

        rerank_function = strategy_map.get(self.config.reranking_strategy)

        if rerank_function:
            if self.config.reranking_strategy in [
                RerankingStrategy.CONTEXTUAL_BOOST,
                RerankingStrategy.COMBINED,
            ]:
                return await rerank_function(query, top_k_results, user_context)
            return await rerank_function(query, top_k_results)

        return results

    async def _cross_encoder_rerank(
        self, query: str, results: list[EnhancedSearchResult]
    ) -> list[EnhancedSearchResult]:
        """Rerank using a cross-encoder model."""
        if self.config.cross_encoder_model == "openai" and self.openai_client:
            return await self._openai_cross_encoder_rerank(query, results)
        if self.config.cross_encoder_model == "bge" and self.bge_reranker:
            return self._bge_cross_encoder_rerank(query, results)
        return results

    async def _openai_cross_encoder_rerank(
        self, query: str, results: list[EnhancedSearchResult]
    ) -> list[EnhancedSearchResult]:
        """Rerank using OpenAI's API as a cross-encoder."""
        try:
            if not self.openai_client:
                self.logger.warning("OpenAI client not available for reranking.")
                return results

            tasks = []
            for result in results:
                prompt = (
                    f"Query: {query}\n\n"
                    f"Document: {result.content}\n\n"
                    "Is the document relevant to the query? Respond with 'Yes' or 'No' and a relevance score from 0.0 to 1.0."
                )
                tasks.append(
                    self.openai_client.completions.create(
                        model="text-davinci-003",
                        prompt=prompt,
                        max_tokens=10,
                        temperature=0,
                    )
                )

            responses = await asyncio.gather(*tasks, return_exceptions=True)
            reranked_results = []

            for i, response in enumerate(responses):
                if isinstance(response, Exception):
                    self.logger.error(
                        f"OpenAI reranking failed for result {results[i].id}: {response}"
                    )
                    results[i].rerank_score = 0.0
                    reranked_results.append(results[i])
                    continue

                try:
                    response = cast(Completion, response)
                    text = response.choices[0].text.strip().lower()
                    score_part = text.split()[-1]
                    score = float(score_part)

                    if "yes" in text and score >= self.config.cross_encoder_threshold:
                        results[i].rerank_score = score
                        reranked_results.append(results[i])

                except (ValueError, IndexError) as e:
                    self.logger.warning(
                        f"Could not parse OpenAI reranking response: '{text}'. Error: {e}"
                    )
                    results[i].rerank_score = 0.0
                    reranked_results.append(results[i])

            reranked_results.sort(key=lambda x: x.rerank_score, reverse=True)
            return reranked_results

        except Exception as e:
            self.logger.error(f"OpenAI cross-encoder reranking failed: {e}")
            return results

    def _bge_cross_encoder_rerank(
        self, query: str, results: list[EnhancedSearchResult]
    ) -> list[EnhancedSearchResult]:
        """Rerank using BGE cross-encoder."""
        if not self.bge_reranker:
            return results

        try:
            sentence_pairs = [[query, result.content] for result in results]
            scores = self.bge_reranker.compute_score(sentence_pairs)

            for result, score in zip(results, scores, strict=False):
                result.rerank_score = float(score)

            results.sort(key=lambda x: x.rerank_score, reverse=True)
            return [
                r
                for r in results
                if r.rerank_score >= self.config.cross_encoder_threshold
            ]

        except Exception as e:
            self.logger.error(f"BGE cross-encoder reranking failed: {e}")
            return results

    def _diversity_rerank(
        self, query: str, results: list[EnhancedSearchResult]
    ) -> list[EnhancedSearchResult]:
        """Rerank for diversity using Maximal Marginal Relevance (MMR)."""
        if not results:
            return []

        reranked_results = [results[0]]
        remaining_results = results[1:]

        lambda_param = self.config.diversity_lambda

        while remaining_results and len(reranked_results) < len(results):
            best_result = None
            max_mmr_score = -float("inf")

            for result in remaining_results:
                relevance_score = result.combined_score
                similarity_scores = [
                    self._calculate_content_similarity(result, reranked)
                    for reranked in reranked_results
                ]
                max_similarity = max(similarity_scores) if similarity_scores else 0.0
                mmr_score = (
                    lambda_param * relevance_score - (1 - lambda_param) * max_similarity
                )

                if mmr_score > max_mmr_score:
                    max_mmr_score = mmr_score
                    best_result = result

            if best_result:
                reranked_results.append(best_result)
                remaining_results.remove(best_result)
            else:
                break  # No more results to add

        for i, result in enumerate(reranked_results):
            result.rerank_score = 1.0 - (i * 0.05)  # Assign rank-based score

        return reranked_results

    def _temporal_rerank(
        self, results: list[EnhancedSearchResult]
    ) -> list[EnhancedSearchResult]:
        """Rerank based on temporal relevance."""
        now = datetime.now()
        for result in results:
            timestamp_str = result.metadata.get("updated_at") or result.metadata.get(
                "created_at"
            )
            timestamp = self._parse_timestamp(timestamp_str) if timestamp_str else None

            if timestamp:
                age_days = (now - timestamp).days
                decay = 1.0 / (1.0 + self.config.temporal_decay_factor * age_days)
                boost = (
                    self.config.temporal_boost_recent
                    if age_days <= self.config.temporal_recent_threshold_days
                    else 1.0
                )
                result.rerank_score = result.combined_score * decay * boost
            else:
                result.rerank_score = (
                    result.combined_score * 0.8
                )  # Penalize no timestamp

        results.sort(key=lambda x: x.rerank_score, reverse=True)
        return results

    def _contextual_rerank(
        self,
        query: str,
        results: list[EnhancedSearchResult],
        user_context: dict[str, Any] | None = None,
    ) -> list[EnhancedSearchResult]:
        """Rerank based on user context."""
        if not user_context:
            return results

        user_history = user_context.get("history", [])
        preferred_sources = user_context.get("preferred_sources", [])

        for result in results:
            boost = 1.0
            if result.source_type in preferred_sources:
                boost *= self.config.context_boost_factor
            if any(
                self._calculate_content_similarity(result, past_result) > 0.8
                for past_result in user_history
            ):
                boost *= self.config.context_boost_factor

            result.rerank_score = result.combined_score * boost

        results.sort(key=lambda x: x.rerank_score, reverse=True)
        return results

    async def _combined_rerank(
        self,
        query: str,
        results: list[EnhancedSearchResult],
        user_context: dict[str, Any] | None = None,
    ) -> list[EnhancedSearchResult]:
        """Combined reranking strategy."""
        # 1. Cross-encoder for initial relevance filtering
        reranked = await self._cross_encoder_rerank(query, results)
        # 2. Temporal reranking
        reranked = self._temporal_rerank(reranked)
        # 3. Diversity reranking
        reranked = self._diversity_rerank(query, reranked)
        # 4. Contextual boost
        if user_context:
            reranked = self._contextual_rerank(query, reranked, user_context)

        return reranked

    def _calculate_content_similarity(
        self, result1: EnhancedSearchResult, result2: EnhancedSearchResult
    ) -> float:
        """Calculate content similarity using Jaccard index."""
        set1 = set(result1.content.lower().split())
        set2 = set(result2.content.lower().split())
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        return intersection / union if union > 0 else 0.0

    def _parse_timestamp(self, timestamp_str: str | None) -> datetime | None:
        """Parse timestamp string into datetime object."""
        if timestamp_str is None:
            return None

        # Handle ISO format with Z (UTC)
        if timestamp_str.endswith("Z"):
            timestamp_str = timestamp_str[:-1] + "+00:00"

        # Handle various formats
        formats_to_try = [
            "%Y-%m-%dT%H:%M:%S.%f%z",  # With microseconds and timezone
            "%Y-%m-%dT%H:%M:%S%z",  # Without microseconds, with timezone
            "%Y-%m-%dT%H:%M:%S",  # Without microseconds or timezone
            "%Y-%m-%d %H:%M:%S",  # Space separator
        ]

        for fmt in formats_to_try:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except (ValueError, TypeError):
                continue

        self.logger.warning(f"Could not parse timestamp: {timestamp_str}")
        return None
