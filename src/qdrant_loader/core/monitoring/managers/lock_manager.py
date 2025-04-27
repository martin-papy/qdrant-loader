"""
Async lock manager for performance monitoring.
"""

import asyncio
import time
from typing import Optional, Dict
from qdrant_loader.core.monitoring.exceptions import OperationTimeoutError
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class AsyncLockManager:
    """Manages async locks with timeouts and retries."""
    def __init__(self, timeout: float = 5.0, max_retries: int = 3, retry_delay: float = 0.1):
        self.lock = asyncio.Lock()
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._current_holder: Optional[str] = None
        self._lock_acquire_time: Optional[float] = None
        self._failed_attempts: Dict[str, int] = {}

    async def acquire(self, holder: Optional[str] = None):
        """Acquire the lock with timeout and retries."""
        holder_id = holder or "unknown"
        self._failed_attempts.setdefault(holder_id, 0)
        
        for attempt in range(self.max_retries):
            try:
                # Simple timeout-based acquisition
                acquired = await asyncio.wait_for(self.lock.acquire(), timeout=self.timeout)
                if acquired:
                    self._current_holder = holder
                    self._lock_acquire_time = time.time()
                    self._failed_attempts[holder_id] = 0
                    logger.debug(
                        "Lock acquired",
                        holder=holder,
                        attempt=attempt + 1
                    )
                    return
            except asyncio.TimeoutError:
                self._failed_attempts[holder_id] += 1
                if attempt < self.max_retries - 1:
                    logger.warning(
                        "Lock acquisition failed",
                        holder=holder,
                        attempt=attempt + 1,
                        current_holder=self._current_holder,
                        lock_held_time=time.time() - (self._lock_acquire_time or 0),
                        failed_attempts=self._failed_attempts[holder_id]
                    )
                    await asyncio.sleep(self.retry_delay)
                else:
                    # On final attempt, try to force release
                    if self.lock.locked():
                        try:
                            self.lock.release()
                            logger.warning(
                                "Lock force released on final attempt",
                                previous_holder=self._current_holder
                            )
                        except RuntimeError:
                            pass
                    raise OperationTimeoutError(
                        f"Failed to acquire lock after {self.max_retries} attempts. "
                        f"Current holder: {self._current_holder}"
                    )

    async def release(self):
        """Release the lock."""
        try:
            if self.lock.locked():
                previous_holder = self._current_holder
                self._current_holder = None
                self._lock_acquire_time = None
                self.lock.release()
                logger.debug(
                    "Lock released",
                    previous_holder=previous_holder
                )
        except Exception as e:
            logger.error(f"Error during release: {e}", exc_info=True)

    async def __aenter__(self):
        """Async context manager entry."""
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.release()

    async def cleanup(self):
        """Clean up resources."""
        try:
            if self.lock.locked():
                self.lock.release()
            self._current_holder = None
            self._lock_acquire_time = None
            self._failed_attempts.clear()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True) 