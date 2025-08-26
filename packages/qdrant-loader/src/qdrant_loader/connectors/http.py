"""Legacy HTTP utilities shim.

This module re-exports the shared HTTP client utilities to keep backward
compatibility with existing imports. New code should import from
`qdrant_loader.connectors.shared.http` instead.
"""

from qdrant_loader.connectors.shared.http import (  # noqa: F401
    aiohttp_request_with_retries,
    make_request_async,
    make_request_with_retries_async,
)
