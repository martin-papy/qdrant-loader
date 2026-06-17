"""
FastMCP application scaffold (migration target).

This module lives alongside the existing hand-rolled JSON_RPC
server (server.py/ cli.py) and is not yet wired into any entry point.
It builds the FastMCP instance and the lifespan that owns heavy resources
(SearchEngine, QueryProcessor). Tools are registerred later

Resource lifecycle mirrors server.py: heavy imports and initialization
happen inside the lifespan (after the event loop is up), not at module import time.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from .utils import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


@asynccontextmanager
async def _lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Build heavy resources on startup; clean them up on shutdown
    Whatever this yields becomes ``ctx.lifespan_context`` inside every tool.
    """
    # Lazy imports keep module import cheap
    from .config_loader import load_config
    from .mcp.protocol import MCPProtocol
    from .mcp.search_handler import SearchHandler
    from .search.engine import SearchEngine
    from .search.processor import QueryProcessor

    config_path = os.getenv("MCP_CONFIG")
    config, _, _ = load_config(Path(config_path) if config_path else None)

    search_engine = SearchEngine()
    query_processor = QueryProcessor(config.openai)

    try:
        await search_engine.initialize(config.qdrant, config.openai, config.search)
        logger.info("FastMCP search engine initialized", pid=os.getpid())
        # Reuse the existing handler for its reranker
        # Built after initialize() so the hybrid pipeline exists
        search_handler = SearchHandler(
            search_engine=search_engine,
            query_processor=query_processor,
            protocol=MCPProtocol(),
            reranking_config=config.reranking,
        )
        yield {
            "search_engine": search_engine,
            "query_processor": query_processor,
            "config": config,
            "search_handler": search_handler,
        }
    finally:
        try:
            await search_engine.cleanup()
        except Exception:
            logger.error("Error during FastMCP search engine cleanup", exc_info=True)


# The FastMCP app. Imported by entry points later
mcp = FastMCP("Qdrant Loader MCP Server", lifespan=_lifespan)

# Register tools onto the instance
# tool modules pull only fastmcp/pydantic, not the search engine
from .fastmcp_tools import register_all  # noqa: E402

register_all(mcp)
