"""Search engine service for the MCP server."""

from openai import AsyncOpenAI
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models

from ..config import OpenAIConfig, QdrantConfig
from ..utils.logging import LoggingConfig
from .hybrid_search import HybridSearchEngine
from .models import SearchResult
# 🔥 NEW: Import Phase 1.2 topic chaining components
from .enhanced.topic_search_chain import TopicSearchChain, ChainStrategy

logger = LoggingConfig.get_logger(__name__)


class SearchEngine:
    """Main search engine that orchestrates query processing and search."""

    def __init__(self):
        """Initialize the search engine."""
        self.client: AsyncQdrantClient | None = None
        self.config: QdrantConfig | None = None
        self.openai_client: AsyncOpenAI | None = None
        self.hybrid_search: HybridSearchEngine | None = None
        self.logger = LoggingConfig.get_logger(__name__)

    async def initialize(
        self, config: QdrantConfig, openai_config: OpenAIConfig
    ) -> None:
        """Initialize the search engine with configuration."""
        self.config = config
        try:
            self.client = AsyncQdrantClient(url=config.url, api_key=config.api_key)
            self.openai_client = AsyncOpenAI(api_key=openai_config.api_key)

            # Ensure collection exists
            if self.client is None:
                raise RuntimeError("Failed to initialize Qdrant client")

            collections = await self.client.get_collections()
            if not any(c.name == config.collection_name for c in collections.collections):
                await self.client.create_collection(
                    collection_name=config.collection_name,
                    vectors_config=models.VectorParams(
                        size=1536,  # Default size for OpenAI embeddings
                        distance=models.Distance.COSINE,
                    ),
                )

            # Initialize hybrid search
            if self.client and self.openai_client:
                self.hybrid_search = HybridSearchEngine(
                    qdrant_client=self.client,
                    openai_client=self.openai_client,
                    collection_name=config.collection_name,
                )

            self.logger.info("Successfully connected to Qdrant", url=config.url)
        except Exception as e:
            self.logger.error(
                "Failed to connect to Qdrant server",
                error=str(e),
                url=config.url,
                hint="Make sure Qdrant is running and accessible at the configured URL",
            )
            raise RuntimeError(
                f"Failed to connect to Qdrant server at {config.url}. "
                "Please ensure Qdrant is running and accessible."
            ) from None  # Suppress the original exception

    async def cleanup(self) -> None:
        """Cleanup resources."""
        if self.client:
            await self.client.close()
            self.client = None

    async def search(
        self,
        query: str,
        source_types: list[str] | None = None,
        limit: int = 5,
        project_ids: list[str] | None = None,
    ) -> list[SearchResult]:
        """Search for documents using hybrid search.

        Args:
            query: Search query text
            source_types: Optional list of source types to filter by
            limit: Maximum number of results to return
            project_ids: Optional list of project IDs to filter by
        """
        if not self.hybrid_search:
            raise RuntimeError("Search engine not initialized")

        self.logger.debug(
            "Performing search",
            query=query,
            source_types=source_types,
            limit=limit,
            project_ids=project_ids,
        )

        try:
            results = await self.hybrid_search.search(
                query=query,
                source_types=source_types,
                limit=limit,
                project_ids=project_ids,
            )

            self.logger.info(
                "Search completed",
                query=query,
                result_count=len(results),
                project_ids=project_ids,
            )

            return results
        except Exception as e:
            self.logger.error("Search failed", error=str(e), query=query)
            raise
    
    async def generate_topic_chain(
        self,
        query: str,
        strategy: str = "mixed_exploration",
        max_links: int = 5
    ) -> TopicSearchChain:
        """🔥 NEW: Generate a topic-driven search chain for progressive discovery.
        
        Args:
            query: Original search query
            strategy: Chain generation strategy (breadth_first, depth_first, relevance_ranked, mixed_exploration)
            max_links: Maximum number of chain links to generate
            
        Returns:
            TopicSearchChain with progressive exploration queries
        """
        if not self.hybrid_search:
            raise RuntimeError("Search engine not initialized")

        # Convert string strategy to enum
        try:
            chain_strategy = ChainStrategy(strategy)
        except ValueError:
            self.logger.warning(f"Unknown strategy '{strategy}', using mixed_exploration")
            chain_strategy = ChainStrategy.MIXED_EXPLORATION

        self.logger.debug(
            "Generating topic search chain",
            query=query,
            strategy=strategy,
            max_links=max_links
        )

        try:
            topic_chain = await self.hybrid_search.generate_topic_search_chain(
                query=query,
                strategy=chain_strategy,
                max_links=max_links
            )

            self.logger.info(
                "Topic chain generation completed",
                query=query,
                chain_length=len(topic_chain.chain_links),
                topics_covered=topic_chain.total_topics_covered,
                discovery_potential=f"{topic_chain.estimated_discovery_potential:.2f}"
            )

            return topic_chain
        except Exception as e:
            self.logger.error("Topic chain generation failed", error=str(e), query=query)
            raise
    
    async def execute_topic_chain(
        self,
        topic_chain: TopicSearchChain,
        results_per_link: int = 3,
        source_types: list[str] | None = None,
        project_ids: list[str] | None = None
    ) -> dict[str, list[SearchResult]]:
        """🔥 NEW: Execute searches for all links in a topic chain.
        
        Args:
            topic_chain: The topic search chain to execute
            results_per_link: Number of results per chain link
            source_types: Optional source type filters
            project_ids: Optional project ID filters
            
        Returns:
            Dictionary mapping queries to search results
        """
        if not self.hybrid_search:
            raise RuntimeError("Search engine not initialized")

        self.logger.debug(
            "Executing topic chain search",
            original_query=topic_chain.original_query,
            chain_length=len(topic_chain.chain_links),
            results_per_link=results_per_link
        )

        try:
            chain_results = await self.hybrid_search.execute_topic_chain_search(
                topic_chain=topic_chain,
                results_per_link=results_per_link,
                source_types=source_types,
                project_ids=project_ids
            )

            total_results = sum(len(results) for results in chain_results.values())
            self.logger.info(
                "Topic chain execution completed",
                original_query=topic_chain.original_query,
                total_queries=len(chain_results),
                total_results=total_results
            )

            return chain_results
        except Exception as e:
            self.logger.error("Topic chain execution failed", error=str(e))
            raise
    
    async def search_with_topic_chain(
        self,
        query: str,
        strategy: str = "mixed_exploration",
        max_links: int = 5,
        results_per_link: int = 3,
        source_types: list[str] | None = None,
        project_ids: list[str] | None = None
    ) -> dict[str, list[SearchResult]]:
        """🔥 NEW: Combined method to generate and execute a topic search chain.
        
        Args:
            query: Original search query
            strategy: Chain generation strategy
            max_links: Maximum chain links
            results_per_link: Results per link
            source_types: Optional source filters
            project_ids: Optional project filters
            
        Returns:
            Dictionary mapping chain queries to their results
        """
        self.logger.debug(
            "Starting topic chain search workflow",
            query=query,
            strategy=strategy,
            max_links=max_links,
            results_per_link=results_per_link
        )

        try:
            # Generate topic chain
            topic_chain = await self.generate_topic_chain(
                query=query,
                strategy=strategy,
                max_links=max_links
            )

            # Execute the chain
            chain_results = await self.execute_topic_chain(
                topic_chain=topic_chain,
                results_per_link=results_per_link,
                source_types=source_types,
                project_ids=project_ids
            )

            self.logger.info(
                "Topic chain search workflow completed",
                query=query,
                total_queries=len(chain_results),
                total_results=sum(len(results) for results in chain_results.values()),
                discovery_potential=f"{topic_chain.estimated_discovery_potential:.2f}"
            )

            return chain_results
        except Exception as e:
            self.logger.error("Topic chain search workflow failed", error=str(e), query=query)
            raise
