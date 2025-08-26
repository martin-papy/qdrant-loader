from __future__ import annotations

import asyncio


class RateLimiter:
    """Simple async rate limiter enforcing a minimum interval between calls.

    Default factory `per_minute` configures a per-minute limit.
    """

    def __init__(
        self,
        *,
        requests_per_interval: int,
        interval_seconds: float = 60.0,
    ) -> None:
        if requests_per_interval <= 0:
            raise ValueError("requests_per_interval must be > 0")
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be > 0")

        self._min_interval: float = interval_seconds / float(requests_per_interval)
        self._lock: asyncio.Lock = asyncio.Lock()
        self._last_request_time: float | None = None

    @classmethod
    def per_minute(cls, requests_per_minute: int) -> RateLimiter:
        return cls(requests_per_interval=requests_per_minute, interval_seconds=60.0)

    def _get_delay(self, now: float) -> float:
        if self._last_request_time is None:
            return 0.0
        elapsed = now - self._last_request_time
        delay = self._min_interval - elapsed
        return delay if delay > 0.0 else 0.0

    async def acquire(self) -> None:
        async with self._lock:
            loop = asyncio.get_running_loop()
            now = loop.time()
            delay = self._get_delay(now)
            if delay > 0:
                await asyncio.sleep(delay)
                now = loop.time()
            self._last_request_time = now

    async def __aenter__(self) -> RateLimiter:
        await self.acquire()
        return self

    async def __aexit__(
        self, exc_type, exc, tb
    ) -> None:  # noqa: D401 (intentional no-op)
        # No cleanup required
        return None
