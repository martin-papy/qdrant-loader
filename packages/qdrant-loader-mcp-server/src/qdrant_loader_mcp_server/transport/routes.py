"""FastAPI router for MCP HTTP transport endpoints."""

import asyncio
import json
import time

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from ..utils.logging import LoggingConfig
from .dependencies import get_mcp_handler, validate_origin

logger = LoggingConfig.get_logger(__name__)

mcp_router = APIRouter()


@mcp_router.post("/mcp", dependencies=[Depends(validate_origin)])
async def handle_mcp_post(
    request: Request,
    mcp_handler=Depends(get_mcp_handler),
):
    """Handle client-to-server messages via HTTP POST."""
    try:
        body = await request.json()
    except json.JSONDecodeError:
        logger.error("Invalid JSON in request body")
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32700, "message": "Invalid JSON in request"},
        }

    try:
        logger.debug("Processing MCP request: %s", body.get("method", "unknown"))
        response = await mcp_handler.handle_request(body, headers=dict(request.headers))
        logger.debug("Successfully processed MCP request")
        return response
    except Exception:
        logger.error("Error processing MCP request", exc_info=True)
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": "Internal server error"},
        }


@mcp_router.get("/mcp")
async def handle_mcp_get():
    """SSE stub -- heartbeat-only stream for keep-alive."""

    async def heartbeat():
        try:
            while True:
                yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': time.time()})}\n\n"
                await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            logger.debug("SSE heartbeat stream cancelled")
            raise

    return StreamingResponse(
        heartbeat(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
