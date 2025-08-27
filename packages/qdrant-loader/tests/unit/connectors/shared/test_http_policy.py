from unittest.mock import AsyncMock, patch

import pytest
from qdrant_loader.connectors.shared.http.policy import (
    aiohttp_request_with_policy,
    request_with_policy,
)
from qdrant_loader.connectors.shared.http.rate_limit import RateLimiter


@pytest.mark.asyncio
async def test_request_with_policy_invokes_retries_and_rate_limiter():
    class DummyResponse:
        def __init__(self, status_code: int):
            self.status_code = status_code

        def raise_for_status(self):
            return None

    async def fake_make_request_with_retries_async(session, method, url, **kwargs):
        return DummyResponse(status_code=200)

    limiter = RateLimiter.per_minute(600)  # ~100ms min interval, fast for tests

    with (
        patch(
            "qdrant_loader.connectors.shared.http.policy.make_request_with_retries_async",
            new=AsyncMock(side_effect=fake_make_request_with_retries_async),
        ) as mock_retry_call,
        patch.object(limiter, "acquire", new=AsyncMock()) as mock_acquire,
    ):
        # Use a minimal fake requests.Session
        class DummySession:
            def request(self, *args, **kwargs):
                return DummyResponse(200)

        resp = await request_with_policy(
            DummySession(),
            "GET",
            "https://example.com",
            rate_limiter=limiter,
            overall_timeout=2.0,
        )

        assert isinstance(resp, DummyResponse)
        mock_retry_call.assert_awaited()
        mock_acquire.assert_awaited()


@pytest.mark.asyncio
async def test_aiohttp_request_with_policy_invokes_retries_and_rate_limiter():
    class DummyAiohttpResponse:
        def __init__(self, status: int = 200):
            self.status = status

        async def release(self):
            return None

        async def text(self):
            return "ok"

    async def fake_aiohttp_request_with_retries(session, method, url, **kwargs):
        return DummyAiohttpResponse(status=200)

    limiter = RateLimiter.per_minute(600)

    with (
        patch(
            "qdrant_loader.connectors.shared.http.policy.aiohttp_request_with_retries",
            new=AsyncMock(side_effect=fake_aiohttp_request_with_retries),
        ) as mock_retry_call,
        patch.object(limiter, "acquire", new=AsyncMock()) as mock_acquire,
    ):

        class DummyAiohttpSession:
            async def get(self, *args, **kwargs):
                return DummyAiohttpResponse(200)

            async def request(self, *args, **kwargs):
                return DummyAiohttpResponse(200)

        resp = await aiohttp_request_with_policy(
            DummyAiohttpSession(),
            "GET",
            "https://example.com",
            rate_limiter=limiter,
            overall_timeout=2.0,
        )

        assert isinstance(resp, DummyAiohttpResponse)
        mock_retry_call.assert_awaited()
        mock_acquire.assert_awaited()
