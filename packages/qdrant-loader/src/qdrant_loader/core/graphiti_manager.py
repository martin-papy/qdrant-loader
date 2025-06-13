"""Graphiti client manager for knowledge graph operations.

This module provides a manager class for Graphiti operations,
integrating with the existing Neo4j configuration and connection management.
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType
from graphiti_core.llm_client import OpenAIClient, LLMConfig
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig

from ..config.neo4j import Neo4jConfig
from ..config.graphiti import GraphitiConfig
from ..utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class GraphitiManager:
    """Manager for Graphiti knowledge graph operations."""

    def __init__(
        self,
        neo4j_config: Neo4jConfig,
        graphiti_config: Optional[GraphitiConfig] = None,
        openai_api_key: Optional[str] = None,
    ):
        """Initialize the Graphiti manager.

        Args:
            neo4j_config: Neo4j configuration object
            graphiti_config: Graphiti configuration object with LLM and embedder settings
            openai_api_key: OpenAI API key for LLM and embedding operations (overrides config)
        """
        self.neo4j_config = neo4j_config
        self.graphiti_config = graphiti_config or GraphitiConfig()

        # Use provided API key or fall back to config
        self.openai_api_key = (
            openai_api_key
            or self.graphiti_config.llm.api_key
            or self.graphiti_config.embedder.api_key
        )

        self._graphiti: Optional[Graphiti] = None
        self._llm_client: Optional[OpenAIClient] = None
        self._embedder: Optional[OpenAIEmbedder] = None
        self._initialized = False

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    def _create_llm_client(self) -> OpenAIClient:
        """Create and configure the OpenAI LLM client.

        Returns:
            Configured OpenAI LLM client

        Raises:
            ValueError: If OpenAI API key is not provided
        """
        if not self.openai_api_key:
            raise ValueError(
                "OpenAI API key is required for LLM operations. "
                "Provide it via constructor parameter or GraphitiConfig."
            )

        llm_config = LLMConfig(
            api_key=self.openai_api_key,
            model=self.graphiti_config.llm.model,
            max_tokens=self.graphiti_config.llm.max_tokens,
            temperature=self.graphiti_config.llm.temperature,
        )

        logger.debug(
            f"Creating OpenAI LLM client with model: {self.graphiti_config.llm.model}"
        )

        return OpenAIClient(config=llm_config)

    def _create_embedder(self) -> OpenAIEmbedder:
        """Create and configure the OpenAI embedder.

        Returns:
            Configured OpenAI embedder

        Raises:
            ValueError: If OpenAI API key is not provided
        """
        if not self.openai_api_key:
            raise ValueError(
                "OpenAI API key is required for embedding operations. "
                "Provide it via constructor parameter or GraphitiConfig."
            )

        embedder_config = OpenAIEmbedderConfig(
            embedding_model=self.graphiti_config.embedder.model,
            api_key=self.openai_api_key,
        )

        # Add dimensions if specified and supported by the model
        if self.graphiti_config.embedder.dimensions:
            embedder_config.embedding_dim = self.graphiti_config.embedder.dimensions

        logger.debug(
            f"Creating OpenAI embedder with model: {self.graphiti_config.embedder.model}"
        )

        return OpenAIEmbedder(config=embedder_config)

    async def initialize(self) -> None:
        """Initialize the Graphiti client and build indices."""
        if self._initialized:
            logger.debug("Graphiti manager already initialized")
            return

        try:
            logger.info("Initializing Graphiti client with Neo4j configuration")

            # Create LLM client and embedder
            self._llm_client = self._create_llm_client()
            self._embedder = self._create_embedder()

            # Initialize Graphiti with Neo4j connection parameters and AI components
            self._graphiti = Graphiti(
                uri=self.neo4j_config.uri,
                user=self.neo4j_config.user,
                password=self.neo4j_config.password,
                llm_client=self._llm_client,
                embedder=self._embedder,
            )

            # Build indices and constraints (only needs to be done once)
            if self.graphiti_config.operational.enable_auto_indexing:
                logger.info("Building Graphiti indices and constraints")
                await self._graphiti.build_indices_and_constraints()
            else:
                logger.info("Auto-indexing disabled, skipping index creation")

            self._initialized = True
            logger.info(
                f"Graphiti client initialized successfully with "
                f"LLM model: {self.graphiti_config.llm.model}, "
                f"Embedder model: {self.graphiti_config.embedder.model}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize Graphiti client: {e}")
            raise

    async def close(self) -> None:
        """Close the Graphiti client connection."""
        if self._graphiti:
            try:
                await self._graphiti.close()
                logger.info("Graphiti client connection closed")
            except Exception as e:
                logger.error(f"Error closing Graphiti client: {e}")
            finally:
                self._graphiti = None
                self._llm_client = None
                self._embedder = None
                self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """Check if the Graphiti client is initialized."""
        return self._initialized and self._graphiti is not None

    @property
    def client(self) -> Graphiti:
        """Get the Graphiti client instance."""
        if not self.is_initialized or self._graphiti is None:
            raise RuntimeError(
                "Graphiti client not initialized. Call initialize() first."
            )
        return self._graphiti

    @property
    def llm_client(self) -> Optional[OpenAIClient]:
        """Get the LLM client instance."""
        return self._llm_client

    @property
    def embedder(self) -> Optional[OpenAIEmbedder]:
        """Get the embedder instance."""
        return self._embedder

    async def add_episode(
        self,
        name: str,
        content: str,
        episode_type: EpisodeType = EpisodeType.text,
        source_description: Optional[str] = None,
        reference_time: Optional[datetime] = None,
        **kwargs,
    ) -> str:
        """Add an episode to the knowledge graph.

        Args:
            name: Name/identifier for the episode
            content: Content of the episode (text or JSON string)
            episode_type: Type of episode (text or json)
            source_description: Description of the source
            reference_time: Reference timestamp for the episode
            **kwargs: Additional parameters for episode creation

        Returns:
            Episode UUID

        Raises:
            RuntimeError: If client is not initialized
        """
        if not self.is_initialized or self._graphiti is None:
            raise RuntimeError("Graphiti client not initialized")

        try:
            reference_time = reference_time or datetime.now(timezone.utc)

            logger.debug(f"Adding episode: {name} (type: {episode_type.value})")

            result = await self._graphiti.add_episode(
                name=name,
                episode_body=content,
                source=episode_type,
                source_description=source_description or "QDrant Loader Document",
                reference_time=reference_time,
                **kwargs,
            )

            # Extract episode UUID from the result
            episode_uuid = (
                result.episode.uuid
                if hasattr(result, "episode") and hasattr(result.episode, "uuid")
                else str(result)
            )

            logger.info(f"Successfully added episode: {name} with UUID: {episode_uuid}")
            return episode_uuid

        except Exception as e:
            logger.error(f"Failed to add episode {name}: {e}")
            raise

    async def search(
        self,
        query: str,
        limit: int = 10,
        center_node_uuid: Optional[str] = None,
        **kwargs,
    ) -> List[Any]:
        """Search the knowledge graph.

        Args:
            query: Search query string
            limit: Maximum number of results to return
            center_node_uuid: Optional center node for reranking results
            **kwargs: Additional search parameters

        Returns:
            List of search results

        Raises:
            RuntimeError: If client is not initialized
        """
        if not self.is_initialized or self._graphiti is None:
            raise RuntimeError("Graphiti client not initialized")

        try:
            # Respect configured limits
            limit = min(limit, self.graphiti_config.operational.search_limit_max)

            logger.debug(f"Searching knowledge graph: {query}")

            results = await self._graphiti.search(
                query=query,
                num_results=limit,
                center_node_uuid=center_node_uuid,
                **kwargs,
            )

            logger.info(f"Search returned {len(results)} results for query: {query}")
            return results

        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            raise

    async def get_nodes(
        self, node_uuids: Optional[List[str]] = None, limit: int = 100, **kwargs
    ) -> List[Any]:
        """Retrieve nodes from the knowledge graph.

        Args:
            node_uuids: Optional list of specific node UUIDs to retrieve
            limit: Maximum number of nodes to return
            **kwargs: Additional parameters

        Returns:
            List of nodes

        Raises:
            RuntimeError: If client is not initialized
        """
        if not self.is_initialized or self._graphiti is None:
            raise RuntimeError("Graphiti client not initialized")

        try:
            if node_uuids:
                logger.debug(f"Retrieving {len(node_uuids)} specific nodes")
                # Use search to find specific nodes by UUID
                nodes = []
                for uuid in node_uuids:
                    try:
                        # Search for nodes with specific UUID
                        results = await self._graphiti.search(
                            query=f"uuid:{uuid}",
                            num_results=1,
                        )
                        if results:
                            nodes.extend(results)
                    except Exception as e:
                        logger.warning(f"Failed to retrieve node {uuid}: {e}")
                        continue
                return nodes
            else:
                logger.debug(f"Retrieving up to {limit} nodes via search")
                # Use a broad search to get recent nodes
                # This is a workaround since Graphiti doesn't have a direct "list all nodes" method
                results = await self._graphiti.search(
                    query="*",  # Broad search query
                    num_results=min(
                        limit, self.graphiti_config.operational.search_limit_max
                    ),
                )
                return results

        except Exception as e:
            logger.error(f"Failed to retrieve nodes: {e}")
            raise

    async def get_edges(
        self, edge_uuids: Optional[List[str]] = None, limit: int = 100, **kwargs
    ) -> List[Any]:
        """Retrieve edges from the knowledge graph.

        Args:
            edge_uuids: Optional list of specific edge UUIDs to retrieve
            limit: Maximum number of edges to return
            **kwargs: Additional parameters

        Returns:
            List of edges

        Raises:
            RuntimeError: If client is not initialized
        """
        if not self.is_initialized or self._graphiti is None:
            raise RuntimeError("Graphiti client not initialized")

        try:
            if edge_uuids:
                logger.debug(f"Retrieving {len(edge_uuids)} specific edges")
                # Note: Graphiti's search primarily returns nodes, not edges directly
                # This is a limitation of the current Graphiti API
                logger.warning(
                    "Direct edge retrieval by UUID not fully supported by Graphiti API"
                )
                return []
            else:
                logger.debug(f"Retrieving edges via relationship search")
                # Use search to find relationship information
                # This is limited by Graphiti's current API capabilities
                logger.warning(
                    "General edge listing not directly supported by Graphiti API"
                )
                return []

        except Exception as e:
            logger.error(f"Failed to retrieve edges: {e}")
            raise

    async def get_entities_from_episode(
        self, episode_id: str, entity_types: Optional[List[str]] = None
    ) -> List[Any]:
        """Retrieve entities extracted from a specific episode.

        Args:
            episode_id: UUID of the episode
            entity_types: Optional list of entity types to filter by

        Returns:
            List of entities related to the episode

        Raises:
            RuntimeError: If client is not initialized
        """
        if not self.is_initialized or self._graphiti is None:
            raise RuntimeError("Graphiti client not initialized")

        try:
            logger.debug(f"Retrieving entities from episode: {episode_id}")

            # Search for entities related to the episode
            # Use the episode ID in the search query
            search_query = f"episode:{episode_id}"
            if entity_types:
                # Add entity type filters to the search
                type_filter = " OR ".join([f"type:{et}" for et in entity_types])
                search_query = f"({search_query}) AND ({type_filter})"

            results = await self._graphiti.search(
                query=search_query,
                num_results=100,  # Get more results for entity extraction
            )

            logger.info(f"Found {len(results)} entities for episode {episode_id}")
            return results

        except Exception as e:
            logger.error(f"Failed to retrieve entities from episode {episode_id}: {e}")
            raise

    async def search_entities(
        self, query: str, entity_types: Optional[List[str]] = None, limit: int = 50
    ) -> List[Any]:
        """Search for entities in the knowledge graph.

        Args:
            query: Search query string
            entity_types: Optional list of entity types to filter by
            limit: Maximum number of results to return

        Returns:
            List of matching entities

        Raises:
            RuntimeError: If client is not initialized
        """
        if not self.is_initialized or self._graphiti is None:
            raise RuntimeError("Graphiti client not initialized")

        try:
            # Build search query with entity type filters
            search_query = query
            if entity_types:
                type_filter = " OR ".join([f"type:{et}" for et in entity_types])
                search_query = f"({query}) AND ({type_filter})"

            logger.debug(f"Searching entities with query: {search_query}")

            results = await self._graphiti.search(
                query=search_query,
                num_results=min(
                    limit, self.graphiti_config.operational.search_limit_max
                ),
            )

            logger.info(f"Entity search returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Entity search failed for query '{query}': {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the Graphiti connection.

        Returns:
            Dictionary containing health check results
        """
        health_status = {
            "initialized": self.is_initialized,
            "neo4j_config": {
                "uri": self.neo4j_config.uri,
                "database": self.neo4j_config.database,
                "user": self.neo4j_config.user,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if self.is_initialized:
            try:
                # Test basic functionality by attempting a simple search
                test_results = await self.search("test", limit=1)
                health_status["connection_test"] = "passed"
                health_status["test_search_results"] = len(test_results)
            except Exception as e:
                health_status["connection_test"] = "failed"
                health_status["error"] = str(e)
        else:
            health_status["connection_test"] = "not_initialized"

        return health_status
