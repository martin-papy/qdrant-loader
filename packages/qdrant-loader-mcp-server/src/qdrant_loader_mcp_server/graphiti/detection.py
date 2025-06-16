"""Graphiti detection and integration module."""

import asyncio
import os
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class GraphitiDetector:
    """Detects and manages Graphiti/Neo4j availability."""

    def __init__(self):
        self._graphiti_available: bool | None = None
        self._graphiti_client: Any | None = None
        self._last_check_time: float | None = None
        self._check_interval = 300  # 5 minutes

    def is_configured(self) -> bool:
        """Check if Graphiti is properly configured via environment variables."""
        required_vars = ["NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"]
        configured = all(os.environ.get(var) for var in required_vars)

        if configured:
            logger.info(
                "Graphiti configuration detected",
                neo4j_uri=os.environ.get("NEO4J_URI", "not set"),
            )
        else:
            missing_vars = [var for var in required_vars if not os.environ.get(var)]
            logger.info("Graphiti not configured", missing_vars=missing_vars)

        return configured

    async def is_available(self, force_check: bool = False) -> bool:
        """Check if Graphiti/Neo4j is actually available and connectable."""
        import time

        # Use cached result if recent and not forcing check
        if (
            not force_check
            and self._graphiti_available is not None
            and self._last_check_time is not None
            and time.time() - self._last_check_time < self._check_interval
        ):
            return self._graphiti_available

        # Check configuration first
        if not self.is_configured():
            self._graphiti_available = False
            self._last_check_time = time.time()
            return False

        try:
            # Try to import Graphiti
            from graphiti_core import Graphiti

            # Get connection parameters
            neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
            neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
            neo4j_password = os.environ.get("NEO4J_PASSWORD", "password")

            # Create client if not exists or recreate if config changed
            if self._graphiti_client is None:
                self._graphiti_client = Graphiti(neo4j_uri, neo4j_user, neo4j_password)

            # Test connection with a minimal query
            try:
                # Use a simple search to test connectivity
                # Type ignore for dynamic client access
                await asyncio.wait_for(
                    self._graphiti_client.search("connectivity_test", num_results=1),  # type: ignore
                    timeout=10.0,
                )

                self._graphiti_available = True
                logger.info(
                    "Graphiti connectivity confirmed",
                    neo4j_uri=neo4j_uri,
                    neo4j_user=neo4j_user,
                )

            except TimeoutError:
                logger.warning(
                    "Graphiti connection timeout", neo4j_uri=neo4j_uri, timeout=10.0
                )
                self._graphiti_available = False

            except Exception as search_error:
                logger.warning(
                    "Graphiti search test failed",
                    error=str(search_error),
                    neo4j_uri=neo4j_uri,
                )
                self._graphiti_available = False

        except ImportError as import_error:
            logger.warning("Graphiti import failed", error=str(import_error))
            self._graphiti_available = False

        except Exception as connection_error:
            logger.warning(
                "Graphiti connection failed",
                error=str(connection_error),
                neo4j_uri=os.environ.get("NEO4J_URI", "not set"),
            )
            self._graphiti_available = False

        self._last_check_time = time.time()
        return self._graphiti_available

    def get_client(self) -> object | None:
        """Get the Graphiti client if available."""
        return self._graphiti_client if self._graphiti_available else None

    async def get_capabilities(self) -> dict:
        """Get current capabilities based on Graphiti availability."""
        available = await self.is_available()

        return {
            "graphiti_available": available,
            "graph_operations": available,
            "hybrid_search": available,
            "temporal_queries": available,
            "node_distance_reranking": available,
            "fallback_mode": not available,
            "configuration": {
                "neo4j_uri": os.environ.get("NEO4J_URI", "not configured"),
                "neo4j_user": os.environ.get("NEO4J_USER", "not configured"),
                "neo4j_password_set": bool(os.environ.get("NEO4J_PASSWORD")),
            },
        }


# Global detector instance
_detector = GraphitiDetector()


async def is_graphiti_available(force_check: bool = False) -> bool:
    """Check if Graphiti is available."""
    return await _detector.is_available(force_check)


def is_graphiti_configured() -> bool:
    """Check if Graphiti is configured."""
    return _detector.is_configured()


def get_graphiti_client() -> object | None:
    """Get the Graphiti client if available."""
    return _detector.get_client()


async def get_graphiti_capabilities() -> dict:
    """Get current Graphiti capabilities."""
    return await _detector.get_capabilities()


async def perform_graphiti_search(
    query: str, center_node_uuid: str | None = None, limit: int = 10, **kwargs
) -> list:
    """Perform a Graphiti search if available, otherwise return empty results."""
    client = get_graphiti_client()
    if not client:
        logger.warning("Graphiti search requested but not available", query=query)
        return []

    try:
        if center_node_uuid:
            # Node distance reranking search
            results = await client.search(  # type: ignore
                query, center_node_uuid=center_node_uuid, num_results=limit, **kwargs
            )
        else:
            # Standard hybrid search
            results = await client.search(query, num_results=limit, **kwargs)  # type: ignore

        logger.info(
            "Graphiti search completed",
            query=query,
            results_count=len(results),
            center_node=center_node_uuid,
        )
        return results

    except Exception as e:
        logger.error(
            "Graphiti search failed",
            query=query,
            error=str(e),
            center_node=center_node_uuid,
        )
        return []
