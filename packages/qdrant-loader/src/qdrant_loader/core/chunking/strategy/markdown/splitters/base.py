from __future__ import annotations

from abc import ABC, abstractmethod


class BaseSplitter(ABC):
    """Base class for section splitting strategies."""

    def __init__(self, settings: "Settings"):
        """Initialize the splitter.

        Args:
            settings: Configuration settings
        """
        self.settings = settings
        self.chunk_size = settings.global_config.chunking.chunk_size
        self.chunk_overlap = settings.global_config.chunking.chunk_overlap

    @abstractmethod
    def split_content(self, content: str, max_size: int) -> list[str]:
        """Split content into chunks.

        Args:
            content: Content to split
            max_size: Maximum chunk size

        Returns:
            List of content chunks
        """
        raise NotImplementedError


