"""FastAPI dependencies for the MCP transport layer."""

import re

from fastapi import HTTPException, Request

_ALLOWED_ORIGIN_RE = re.compile(r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$")


async def get_mcp_handler(request: Request):
    """Retrieve the MCP handler from app state.

    Raises HTTPException 503 if the handler has not been initialised yet
    (worker still starting up).
    """
    handler = getattr(request.app.state, "mcp_handler", None)
    if handler is None:
        raise HTTPException(status_code=503, detail="Server is starting up")
    return handler


async def validate_origin(request: Request):
    """Validate the Origin header to prevent DNS rebinding attacks.

    Allows requests without an Origin header (non-browser clients).
    Rejects origins that do not match localhost / 127.0.0.1.
    """
    origin = request.headers.get("origin")
    if not origin:
        return
    if not _ALLOWED_ORIGIN_RE.match(origin):
        raise HTTPException(status_code=403, detail="Invalid origin")
