"""Clean HTTP server entry point.

Architecture:
    Each uvicorn worker process forks and imports this module.  At import
    time only a bare FastAPI shell is created -- zero heavy work.  All
    expensive initialisation (SpaCy, Qdrant client, SearchEngine, thread
    pool) happens inside the async lifespan, which runs once per worker
    after the event loop is up.

    ``uvicorn.run()`` with ``workers=N`` is the *only* uvicorn API that
    actually spawns multiple OS processes.  ``uvicorn.Server.serve()``
    silently ignores ``workers``.

    Configuration is passed to workers via environment variables so each
    forked process can reconstruct it independently.

Usage (via an ASGI server such as uvicorn):
    uvicorn qdrant_loader_mcp_server.server:app --host 0.0.0.0 --port 9090 --workers 4
    python -m uvicorn qdrant_loader_mcp_server.server:app --host 0.0.0.0 --port 9090

This module exposes the ASGI application object ``app``.  It is not
intended to be run directly with ``python -m``.
"""

from __future__ import annotations

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .transport import mcp_router
from .utils import LoggingConfig

# Suppress noisy asyncio debug logging
logging.getLogger("asyncio").setLevel(logging.WARNING)


def _setup_logging(log_level: str) -> None:
    """Initialise logging once per process."""
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)

    level = log_level.upper()
    disable_console = os.getenv("MCP_DISABLE_CONSOLE_LOGGING", "").lower() == "true"
    fmt = "json" if disable_console else "console"
    LoggingConfig.setup(level=level, format=fmt)


# ---------------------------------------------------------------------------
# ASGI app with lazy lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Per-worker startup and shutdown.

    All heavy resources are created here, after fork, with a running
    event loop.  Nothing expensive happens at import time.
    """
    log_level = os.getenv("MCP_LOG_LEVEL", "INFO")
    _setup_logging(log_level)
    logger = LoggingConfig.get_logger(__name__)

    executor = None
    search_engine = None

    try:
        # Lazy imports -- only pulled in once per worker, not at module load
        from .config_loader import load_config
        from .mcp import MCPHandler
        from .search.engine import SearchEngine
        from .search.processor import QueryProcessor

        # Reconstruct config from env / config file
        config_path = os.getenv("MCP_CONFIG")
        config, _, _ = load_config(Path(config_path) if config_path else None)

        # --- Thread pool for CPU-bound work (SpaCy, BM25, reranking) ---
        max_concurrent = getattr(config.search, "max_concurrent_searches", 4)
        pool_size = max(4, max_concurrent + 4)
        executor = ThreadPoolExecutor(
            max_workers=pool_size, thread_name_prefix="mcp-cpu"
        )
        loop = asyncio.get_running_loop()
        loop.set_default_executor(executor)
        logger.info("Worker starting", pid=os.getpid(), pool_size=pool_size)

        # --- Initialise components (SpaCy loads here, not at import) ---
        search_engine = SearchEngine()
        query_processor = QueryProcessor(config.openai)
        mcp_handler = MCPHandler(
            search_engine, query_processor, reranking_config=config.reranking
        )

        await search_engine.initialize(config.qdrant, config.openai, config.search)
        logger.info("Search engine initialised", pid=os.getpid())

        # Store handler on app state so route dependencies can access it
        app.state.mcp_handler = mcp_handler

    except Exception:
        logger.error("Worker failed to start", pid=os.getpid(), exc_info=True)
        # Clean up partially-initialised resources before re-raising
        if hasattr(app.state, "mcp_handler"):
            app.state.mcp_handler = None
        if search_engine:
            try:
                await search_engine.cleanup()
            except Exception:
                logger.error(
                    "Error cleaning up search engine during failed start", exc_info=True
                )
        if executor:
            executor.shutdown(wait=False)
        raise

    yield  # ---- app is serving requests ----

    # --- Shutdown ---
    logger.info("Worker shutting down", pid=os.getpid())
    app.state.mcp_handler = None
    if search_engine:
        try:
            await search_engine.cleanup()
        except Exception:
            logger.error("Error during search engine cleanup", exc_info=True)
    if executor:
        executor.shutdown(wait=False)
    logger.info("Worker cleanup complete", pid=os.getpid())


# Module-level app -- this is what uvicorn imports.  It's just an empty
# FastAPI shell; all real work is deferred to the lifespan above.
app = FastAPI(
    title="QDrant Loader MCP Server",
    lifespan=_lifespan,
)

# Add CORS at the top level so preflight works before lifespan mounts routes
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:[0-9]+)?",
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Include MCP transport routes
app.include_router(mcp_router)


@app.get("/health")
async def health_check(request: Request):
    """Health check -- returns 503 while the worker is still initialising."""
    ready = getattr(request.app.state, "mcp_handler", None) is not None
    body = {
        "status": "healthy" if ready else "starting",
        "transport": "http",
        "protocol": "mcp",
        "pid": os.getpid(),
    }
    if not ready:
        return JSONResponse(content=body, status_code=503)
    return body
