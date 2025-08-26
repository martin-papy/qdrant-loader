"""
Topic Chain Search Operations.

This module implements topic-driven search chain functionality
for progressive discovery and exploration of related content.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core import SearchEngine

from ...utils.logging import LoggingConfig
from ..components.search_result_models import HybridSearchResult
from ..enhanced.topic_search_chain import ChainStrategy, TopicSearchChain

logger = LoggingConfig.get_logger(__name__)


class TopicChainResult(dict):
    """Dict-like result for topic chain searches.

    - Behaves like the legacy mapping of query->results (backward compatible).
    - Additionally exposes metadata via special keys and attributes:
      'chain_results', 'organized_results', and 'stats'.
    """

    def __init__(self, chain_results: dict, organized_results: dict, stats: dict):
        super().__init__(chain_results)
        # Expose as attributes
        self.chain_results = chain_results
        self.organized_results = organized_results
        self.stats = stats

    def __getitem__(self, key):  # type: ignore[override]
        if key == "chain_results":
            return self.chain_results
        if key == "organized_results":
            return self.organized_results
        if key == "stats":
            return self.stats
        return super().__getitem__(key)

    def __contains__(self, key):  # type: ignore[override]
        if key in {"chain_results", "organized_results", "stats"}:
            return True
        return super().__contains__(key)

    def get(self, key, default=None):  # type: ignore[override]
        try:
            return self[key]
        except KeyError:
            return default

    def __eq__(self, other):  # type: ignore[override]
        # Compare only the legacy mapping portion for equality with dicts
        if isinstance(other, dict):
            return dict(super().items()) == other
        return super().__eq__(other)


class TopicChainOperations:
    """Handles topic chain search operations."""

    def __init__(self, engine: SearchEngine):
        """Initialize with search engine reference."""
        self.engine = engine
        self.logger = LoggingConfig.get_logger(__name__)

    async def generate_topic_chain(
        self, query: str, strategy: str = "mixed_exploration", max_links: int = 5
    ) -> TopicSearchChain:
        """🔥 NEW: Generate a topic-driven search chain for progressive discovery.

        Args:
            query: Original search query
            strategy: Chain generation strategy (breadth_first, depth_first, relevance_ranked, mixed_exploration)
            max_links: Maximum number of chain links to generate

        Returns:
            TopicSearchChain with progressive exploration queries
        """
        if not self.engine.hybrid_search:
            raise RuntimeError("Search engine not initialized")

        # Convert string strategy to enum
        try:
            chain_strategy = ChainStrategy(strategy)
        except ValueError:
            self.logger.warning(
                f"Unknown strategy '{strategy}', using mixed_exploration"
            )
            chain_strategy = ChainStrategy.MIXED_EXPLORATION

        self.logger.debug(
            "Generating topic search chain",
            query=query,
            strategy=strategy,
            max_links=max_links,
        )

        try:
            topic_chain = await self.engine.hybrid_search.generate_topic_search_chain(
                query=query, strategy=chain_strategy, max_links=max_links
            )

            self.logger.info(
                "Topic chain generation completed",
                query=query,
                chain_length=len(topic_chain.chain_links),
                topics_covered=topic_chain.total_topics_covered,
                discovery_potential=f"{topic_chain.estimated_discovery_potential:.2f}",
            )

            return topic_chain
        except Exception as e:
            self.logger.error(
                "Topic chain generation failed", error=str(e), query=query
            )
            raise

    async def execute_topic_chain(
        self,
        topic_chain: TopicSearchChain,
        results_per_link: int = 3,
        source_types: list[str] | None = None,
        project_ids: list[str] | None = None,
    ) -> dict[str, list[HybridSearchResult]]:
        """🔥 NEW: Execute searches for all links in a topic chain.

        Args:
            topic_chain: The topic search chain to execute
            results_per_link: Number of results per chain link
            source_types: Optional source type filters
            project_ids: Optional project ID filters

        Returns:
            Dictionary mapping queries to search results
        """
        if not self.engine.hybrid_search:
            raise RuntimeError("Search engine not initialized")

        self.logger.debug(
            "Executing topic chain search",
            original_query=topic_chain.original_query,
            chain_length=len(topic_chain.chain_links),
            results_per_link=results_per_link,
        )

        try:
            chain_results = await self.engine.hybrid_search.execute_topic_chain_search(
                topic_chain=topic_chain,
                results_per_link=results_per_link,
                source_types=source_types,
                project_ids=project_ids,
            )

            total_results = sum(len(results) for results in chain_results.values())
            self.logger.info(
                "Topic chain execution completed",
                original_query=topic_chain.original_query,
                total_queries=len(chain_results),
                total_results=total_results,
            )

            return chain_results
        except Exception as e:
            self.logger.error("Topic chain execution failed", error=str(e))
            raise

    async def search_with_topic_chain(
        self,
        query: str,
        chain_strategy: str = "mixed_exploration",
        results_per_link: int = 3,
        max_links: int = 5,
        source_types: list[str] | None = None,
        project_ids: list[str] | None = None,
    ) -> TopicChainResult:
        """🔥 NEW: Perform search with full topic chain analysis.

        This combines topic chain generation and execution for complete
        progressive discovery workflow.

        Args:
            query: Original search query
            chain_strategy: Strategy for topic chain generation
            results_per_link: Results per chain link
            max_links: Maximum chain links
            source_types: Optional source type filters
            project_ids: Optional project ID filters

        Returns:
            Dictionary with chain metadata and organized results
        """
        if not self.engine.hybrid_search:
            raise RuntimeError("Search engine not initialized")

        self.logger.info(
            "Starting topic chain search workflow",
            query=query,
            strategy=chain_strategy,
            max_links=max_links,
        )

        try:
            # Generate the topic chain
            topic_chain = await self.generate_topic_chain(
                query=query, strategy=chain_strategy, max_links=max_links
            )

            # Execute searches for each link
            chain_results = await self.execute_topic_chain(
                topic_chain=topic_chain,
                results_per_link=results_per_link,
                source_types=source_types,
                project_ids=project_ids,
            )

            # Organize results by exploration depth
            organized_results = self._organize_chain_results(topic_chain, chain_results)

            # Calculate exploration statistics
            stats = self._calculate_exploration_stats(topic_chain, chain_results)

            self.logger.info(
                "Topic chain search completed",
                query=query,
                total_results=sum(len(results) for results in chain_results.values()),
                topics_explored=topic_chain.total_topics_covered,
            )

            # Return structured result matching documented shape while preserving
            # backward compatibility by including raw chain results under a key
            return TopicChainResult(
                chain_results=chain_results,
                organized_results=organized_results,
                stats=stats,
            )

        except Exception as e:
            self.logger.error("Topic chain search failed", error=str(e), query=query)
            raise

    def _organize_chain_results(
        self, topic_chain: TopicSearchChain, chain_results: dict
    ) -> dict:
        """Organize chain results by exploration depth."""
        organized = {}

        # Defensive: handle None or empty chain_results
        if not chain_results:
            return organized

        for link in topic_chain.chain_links:
            depth = link.chain_position
            query = link.query

            if depth not in organized:
                organized[depth] = {
                    "queries": [],
                    "results": [],
                    "total_results": 0,
                }

            results = chain_results.get(query)
            if results is not None:
                organized[depth]["queries"].append(
                    {
                        "query": query,
                        "topics": [link.topic_focus] + link.related_topics,
                        "relevance_score": link.relevance_score,
                        "result_count": len(results),
                    }
                )
                organized[depth]["results"].extend(results)
                organized[depth]["total_results"] += len(results)

        return organized

    def _calculate_exploration_stats(
        self, topic_chain: TopicSearchChain, chain_results: dict
    ) -> dict:
        """Calculate exploration statistics."""
        total_results = sum(len(results) for results in chain_results.values())
        unique_topics = set()

        for link in topic_chain.chain_links:
            unique_topics.update([link.topic_focus] + link.related_topics)

        depth_distribution = {}
        for link in topic_chain.chain_links:
            depth = link.chain_position
            depth_distribution[depth] = depth_distribution.get(depth, 0) + 1

        return {
            "total_chain_links": len(topic_chain.chain_links),
            "unique_topics_discovered": len(unique_topics),
            "depth_distribution": depth_distribution,
            "average_relevance_score": (
                sum(link.relevance_score for link in topic_chain.chain_links)
                / len(topic_chain.chain_links)
                if topic_chain.chain_links
                else 0
            ),
            "results_per_query_average": (
                total_results / len(chain_results) if chain_results else 0
            ),
        }
