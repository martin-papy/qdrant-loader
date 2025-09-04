from __future__ import annotations

import asyncio


class AsyncRateLimiter:
    """Minimal async rate limiter placeholder.

    In later phases, enforce RPM/TPM and concurrency.
    """

    def __init__(self, max_concurrency: int = 5):
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def __aenter__(self):
        await self._semaphore.acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._semaphore.release()
