from __future__ import annotations

import asyncio
from typing import Any

import requests
import random
import asyncio


async def make_request_async(
    session: requests.Session,
    method: str,
    url: str,
    **kwargs: Any,
) -> requests.Response:
    """Execute a requests call in a thread and return the response.

    Caller is responsible for calling response.raise_for_status() and .json() if needed.
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
    """Make an async HTTP request with simple exponential backoff and jitter.

    Retries only on listed status codes and RequestException.
    """
    attempt = 0
    while True:
        try:
            response = await make_request_async(session, method, url, **kwargs)
            if response.status_code in status_forcelist and attempt < retries:
                attempt += 1
                sleep_s = backoff_factor * (2 ** (attempt - 1)) + random.uniform(0, 0.25)
                await asyncio.sleep(sleep_s)
                continue
            return response
        except requests.RequestException:
            if attempt >= retries:
                raise
            attempt += 1
            sleep_s = backoff_factor * (2 ** (attempt - 1)) + random.uniform(0, 0.25)
            await asyncio.sleep(sleep_s)


