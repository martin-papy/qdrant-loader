from __future__ import annotations

import asyncio
import random
from typing import Any

import requests

try:  # Optional import for async HTTP client
    import aiohttp  # type: ignore
except Exception:  # pragma: no cover - optional import for http client
    aiohttp = None  # type: ignore


async def make_request_async(
    session: requests.Session,
    method: str,
    url: str,
    **kwargs: Any,
) -> requests.Response:
    """Execute a `requests` call in a worker thread and return the response.

    Caller is responsible for calling `response.raise_for_status()` and `.json()` if needed.
    """

    def _do_request() -> requests.Response:
        return session.request(method, url, **kwargs)

    return await asyncio.to_thread(_do_request)


async def make_request_with_retries_async(
    session: requests.Session,
    method: str,
    url: str,
    *,
    retries: int = 3,
    backoff_factor: float = 0.5,
    status_forcelist: tuple[int, ...] = (429, 500, 502, 503, 504),
    **kwargs: Any,
) -> requests.Response:
    """Make an async HTTP request with exponential backoff and jitter.

    Retries only on listed status codes and `RequestException`.
    """
    attempt = 0
    while True:
        try:
            response = await make_request_async(session, method, url, **kwargs)
            if response.status_code in status_forcelist and attempt < retries:
                attempt += 1
                sleep_s = backoff_factor * (2 ** (attempt - 1)) + random.uniform(
                    0, 0.25
                )
                await asyncio.sleep(sleep_s)
                continue
            return response
        except requests.RequestException:
            if attempt >= retries:
                raise
            attempt += 1
            sleep_s = backoff_factor * (2 ** (attempt - 1)) + random.uniform(0, 0.25)
            await asyncio.sleep(sleep_s)


async def aiohttp_request_with_retries(
    session: aiohttp.ClientSession,
    method: str,
    url: str,
    *,
    retries: int = 3,
    backoff_factor: float = 0.5,
    status_forcelist: tuple[int, ...] = (429, 500, 502, 503, 504),
    **kwargs: Any,
):
    """Issue an `aiohttp` request with exponential backoff and jitter."""
    attempt = 0
    last_exc: Exception | None = None
    while attempt <= retries:
        try:
            # Prefer method-specific calls (get/post/...) so test doubles that
            # patch e.g. `session.get` still work. Fallback to `request`.
            requester = getattr(session, method.lower(), None)
            if requester is None:
                requester = session.request
            response = (
                await requester(method, url, **kwargs)
                if requester is session.request
                else await requester(url, **kwargs)
            )
            if response.status in status_forcelist and attempt < retries:
                await response.release()
                attempt += 1
                sleep_s = backoff_factor * (2 ** (attempt - 1)) + random.uniform(
                    0, 0.25
                )
                await asyncio.sleep(sleep_s)
                continue
            return response
        except Exception as e:  # pragma: no cover - exercised in integration
            last_exc = e
            if attempt >= retries:
                raise
            attempt += 1
            sleep_s = backoff_factor * (2 ** (attempt - 1)) + random.uniform(0, 0.25)
            await asyncio.sleep(sleep_s)
    if last_exc:
        raise last_exc
