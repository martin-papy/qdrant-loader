import asyncio
from importlib import import_module

import pytest


@pytest.mark.asyncio
async def test_rate_limiter_limits_concurrency():
    mod = import_module("qdrant_loader_core.llm.ratelimit")
    AsyncRateLimiter = mod.AsyncRateLimiter

    limiter = AsyncRateLimiter(max_concurrency=2)

    current = 0
    max_seen = 0
    lock = asyncio.Lock()

    async def work():
        nonlocal current, max_seen
        async with limiter:
            async with lock:
                current += 1
                max_seen = max(max_seen, current)
            # Simulate a bit of work while the permit is held
            await asyncio.sleep(0.05)
            async with lock:
                current -= 1

    await asyncio.gather(*(work() for _ in range(6)))
    assert max_seen <= 2


@pytest.mark.asyncio
async def test_rate_limiter_releases_permit():
    mod = import_module("qdrant_loader_core.llm.ratelimit")
    AsyncRateLimiter = mod.AsyncRateLimiter

    limiter = AsyncRateLimiter(max_concurrency=1)

    current = 0
    max_seen = 0
    lock = asyncio.Lock()

    async def work():
        nonlocal current, max_seen
        async with limiter:
            async with lock:
                current += 1
                max_seen = max(max_seen, current)
            await asyncio.sleep(0.02)
            async with lock:
                current -= 1

    # With concurrency=1, we should never see more than 1 in the critical section
    await asyncio.gather(work(), work(), work())
    assert max_seen == 1
