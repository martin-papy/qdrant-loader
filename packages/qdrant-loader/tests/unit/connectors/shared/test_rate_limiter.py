from __future__ import annotations

import time

import pytest

from qdrant_loader.connectors.shared.http.rate_limit import RateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_allows_first_call_without_delay():
    limiter = RateLimiter(requests_per_interval=10, interval_seconds=1.0)  # 100ms min interval
    start = time.perf_counter()
    await limiter.acquire()
    elapsed = time.perf_counter() - start
    # Should be essentially immediate
    assert elapsed < 0.02


@pytest.mark.asyncio
async def test_rate_limiter_enforces_min_interval():
    limiter = RateLimiter(requests_per_interval=50, interval_seconds=1.0)  # 20ms

    await limiter.acquire()
    start = time.perf_counter()
    await limiter.acquire()
    elapsed = time.perf_counter() - start

    # Should sleep close to 20ms (allow tolerance for scheduler)
    assert elapsed >= 0.015






