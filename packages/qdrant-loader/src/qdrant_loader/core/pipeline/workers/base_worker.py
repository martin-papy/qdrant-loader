"""Base worker interface for pipeline workers."""

import asyncio
from abc import ABC, abstractmethod
from typing import Any

from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class BaseWorker(ABC):
    """Base class for all pipeline workers."""

    def __init__(self, max_workers: int, queue_size: int = 1000):
        self.max_workers = max_workers
        self.queue_size = queue_size
        self.semaphore = asyncio.Semaphore(max_workers)

    @abstractmethod
    async def process(self, input_data: Any) -> Any:
        """Process input data and return result.

        Args:
            input_data: The data to process

        Returns:
            Processed result
        """
        pass

    async def process_with_semaphore(self, input_data: Any) -> Any:
        """Process input data with semaphore control.

        Args:
            input_data: The data to process

        Returns:
            Processed result
        """
        async with self.semaphore:
            return await self.process(input_data)
