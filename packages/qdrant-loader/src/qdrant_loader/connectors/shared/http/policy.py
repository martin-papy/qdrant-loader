from __future__ import annotations

import asyncio
from typing import Any

import requests

from .client import (
    aiohttp_request_with_retries,
    make_request_with_retries_async,
)
from .rate_limit import RateLimiter

DEFAULT_STATUS_FORCELIST: tuple[int, ...] = (429, 500, 502, 503, 504)


async def request_with_policy(
    session: requests.Session,
    method: str,
    url: str,
    *,
    rate_limiter: RateLimiter | None = None,
    retries: int = 3,
    backoff_factor: float = 0.5,
    status_forcelist: tuple[int, ...] = DEFAULT_STATUS_FORCELIST,
    overall_timeout: float | None = None,
    **kwargs: Any,
) -> requests.Response:
    """Perform a requests-based HTTP call with optional rate limiting and retries.

    This helper centralizes our connectors' behavior by combining an optional
    rate limiter with retry-and-jitter semantics.

    Args:
        session: Synchronous requests session (executed via thread offloading)
        method: HTTP method (GET/POST/...)
        url: Target URL
        rate_limiter: Optional async rate limiter enforcing minimum spacing
        retries: Maximum retry attempts for transient failures
        backoff_factor: Base backoff factor for exponential backoff with jitter
        status_forcelist: HTTP status codes that should be retried
        timeout: Optional overall timeout (seconds) applied to the awaitable
        **kwargs: Forwarded to requests.Session.request

    Returns:
        requests.Response
    """

    async def _do_call() -> requests.Response:
        return await make_request_with_retries_async(
            session,
            method,
            url,
            retries=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            **kwargs,
        )

    # Apply rate limiting if provided
    if rate_limiter is not None:
        async with rate_limiter:
            if overall_timeout is not None:
                return await asyncio.wait_for(_do_call(), timeout=overall_timeout)
            return await _do_call()

    # No rate limiter
    if overall_timeout is not None:
        return await asyncio.wait_for(_do_call(), timeout=overall_timeout)
    return await _do_call()


async def aiohttp_request_with_policy(
    session: Any,
    method: str,
    url: str,
    *,
    rate_limiter: RateLimiter | None = None,
    retries: int = 3,
    backoff_factor: float = 0.5,
    status_forcelist: tuple[int, ...] = DEFAULT_STATUS_FORCELIST,
    overall_timeout: float | None = None,
    **kwargs: Any,
):
    """Perform an aiohttp-based HTTP call with optional rate limiting and retries.

    Args mirror request_with_policy but operate on an aiohttp.ClientSession.
    """

    async def _do_call():
        return await aiohttp_request_with_retries(
            session,
            method,
            url,
            retries=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            **kwargs,
        )

    if rate_limiter is not None:
        async with rate_limiter:
            if overall_timeout is not None:
                return await asyncio.wait_for(_do_call(), timeout=overall_timeout)
            return await _do_call()

    if overall_timeout is not None:
        return await asyncio.wait_for(_do_call(), timeout=overall_timeout)
    return await _do_call()
