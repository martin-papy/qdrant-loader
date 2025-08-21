"""Shared HTTP utilities for connectors.

Prefer importing from this package instead of legacy
`qdrant_loader.connectors.http`.
"""

from .client import (
    make_request_async,
    make_request_with_retries_async,
    aiohttp_request_with_retries,
)
from .errors import HTTPRequestError
from .rate_limit import RateLimiter
from .policy import (
    request_with_policy,
    aiohttp_request_with_policy,
)

__all__ = [
    "make_request_async",
    "make_request_with_retries_async",
    "aiohttp_request_with_retries",
    "HTTPRequestError",
    "RateLimiter",
    "request_with_policy",
    "aiohttp_request_with_policy",
]


