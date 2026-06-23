"""FastMCP application for the Qdrant Loader MCP server.

This is the entry point for both transports: ``cli.py`` serves it over stdio
(``mcp.run``) and over HTTP (the module-level ``http_app`` under uvicorn).

Heavy resources (SearchEngine, QueryProcessor, the Search/Intelligence handlers)
are created inside the lifespan — after the event loop is up — not at import time,
so importing this module stays cheap.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from .utils import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


@asynccontextmanager
async def _lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Build heavy resources on startup; clean them up on shutdown
    Whatever this yields becomes ``ctx.lifespan_context`` inside every tool.
    """
    # Lazy imports keep module import cheap
    from .config_loader import load_config
    from .mcp.intelligence_handler import IntelligenceHandler
    from .mcp.protocol import MCPProtocol
    from .mcp.search_handler import SearchHandler
    from .search.engine import SearchEngine
    from .search.processor import QueryProcessor

    config_path = os.getenv("MCP_CONFIG")
    config, _, _ = load_config(Path(config_path) if config_path else None)

    search_engine = SearchEngine()
    query_processor = QueryProcessor(config.openai)
    initialized = False

    try:
        await search_engine.initialize(config.qdrant, config.openai, config.search)
        initialized = True
        logger.info("FastMCP search engine initialized", pid=os.getpid())

        # Reuse the existing handler for its reranker
        # Built after initialize() so the hybrid pipeline exists
        search_handler = SearchHandler(
            search_engine=search_engine,
            query_processor=query_processor,
            protocol=MCPProtocol(),
            reranking_config=config.reranking,
        )

        # Stateful: holds the cluster store shared with expand_cluster
        # build one instance for reuse
        intelligence_handler = IntelligenceHandler(
            search_engine=search_engine, protocol=MCPProtocol()
        )

        yield {
            "search_engine": search_engine,
            "query_processor": query_processor,
            "config": config,
            "search_handler": search_handler,
            "intelligence_handler": intelligence_handler,
        }
    finally:
        if initialized:
            try:
                await search_engine.cleanup()
            except Exception:
                logger.error(
                    "Error during FastMCP search engine cleanup", exc_info=True
                )


# The FastMCP app. Imported by entry points later
mcp = FastMCP("Qdrant Loader MCP Server", lifespan=_lifespan)

# Register tools onto the instance
# tool modules pull only fastmcp/pydantic, not the search engine
from .fastmcp_tools import register_all  # noqa: E402

register_all(mcp)


# ---- HTTP transport surface (used only when served as an ASGI app) ----


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """Liveness probe. The lifespan completes before uvicorn serves traffic,
    so reaching this means the engine is initialized."""
    return JSONResponse(
        {
            "status": "healthy",
            "transport": "http",
            "protocol": "mcp",
            "pid": os.getpid(),
        }
    )


# CORS, secure-by-default
_cors_origins = os.getenv("CORS_ORIGINS", "")
if _cors_origins.strip():
    _allow_origins = [o.strip() for o in _cors_origins.split(",") if o.strip()]
else:
    _allow_origins = ["http://localhost", "http://127.0.0.1"]

_http_middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=_allow_origins,
        allow_credentials=("*" not in _allow_origins),
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
    )
]

# Module-level ASGI app so uvicorn can import it with workers=N
# Tools and /health route must be registered first
http_app = mcp.http_app(
    path="/mcp",
    middleware=_http_middleware,
    # HTTP transport profile: plain JSON responses (no SSE) and stateless
    # request/response (no initialize/session handshake). This is the intended
    # production behavior for simple HTTP clients; stdio is unaffected.
    json_response=True,
    stateless_http=True,
)
