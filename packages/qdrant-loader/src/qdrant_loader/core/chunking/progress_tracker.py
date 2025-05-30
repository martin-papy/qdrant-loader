"""Progress tracking utility for chunking operations."""

import logging
from typing import Dict, Optional
import structlog


class ChunkingProgressTracker:
    """Tracks and reports progress for chunking operations."""

    def __init__(self, logger: structlog.BoundLogger):
        self.logger = logger
        self._progress: Dict[str, Dict] = {}
        # Check if debug mode is enabled by checking the root logger level
        self._is_debug_mode = logging.getLogger().getEffectiveLevel() <= logging.DEBUG

    def start_chunking(
        self,
        document_id: str,
        source: str,
        source_type: str,
        content_length: int,
        file_name: str,
    ) -> None:
        """Start tracking chunking progress for a document."""
        self._progress[document_id] = {
            "source": source,
            "source_type": source_type,
            "content_length": content_length,
            "file_name": file_name,
            "chunks_created": 0,
            "started": True,
        }

        if self._is_debug_mode:
            # Detailed logging for debug mode
            self.logger.debug(
                "Starting chunking",
                extra={
                    "source": source,
                    "source_type": source_type,
                    "content_length": content_length,
                    "file_name": file_name,
                },
            )
        else:
            # Concise logging for info mode
            self.logger.info(f"Chunking {file_name} ({content_length:,} chars)")

    def update_progress(self, document_id: str, chunks_created: int) -> None:
        """Update the number of chunks created for a document."""
        if document_id in self._progress:
            self._progress[document_id]["chunks_created"] = chunks_created

    def finish_chunking(
        self, document_id: str, total_chunks: int, strategy_name: Optional[str] = None
    ) -> None:
        """Finish tracking chunking progress for a document."""
        if document_id not in self._progress:
            return

        progress = self._progress[document_id]

        if self._is_debug_mode:
            # Detailed logging for debug mode
            self.logger.debug(
                "Finished chunking",
                extra={
                    "source": progress["source"],
                    "source_type": progress["source_type"],
                    "file_name": progress["file_name"],
                    "total_chunks": total_chunks,
                    "strategy": strategy_name,
                    "content_length": progress["content_length"],
                },
            )
        else:
            # Concise logging for info mode
            strategy_info = f" using {strategy_name}" if strategy_name else ""
            self.logger.debug(
                f"✓ Created {total_chunks} chunks from {progress['file_name']}{strategy_info}"
            )

        # Clean up
        del self._progress[document_id]

    def log_error(self, document_id: str, error: str) -> None:
        """Log an error during chunking."""
        if document_id in self._progress:
            progress = self._progress[document_id]
            self.logger.error(
                f"Chunking failed for {progress['file_name']}: {error}",
                extra={
                    "source": progress["source"],
                    "source_type": progress["source_type"],
                    "file_name": progress["file_name"],
                    "error": error,
                },
            )
            # Clean up
            del self._progress[document_id]
        else:
            self.logger.error(f"Chunking failed: {error}")

    def log_fallback(self, document_id: str, reason: str) -> None:
        """Log when falling back to default chunking."""
        if document_id in self._progress:
            progress = self._progress[document_id]
            if self._is_debug_mode:
                self.logger.debug(
                    "Falling back to default chunking",
                    extra={
                        "source": progress["source"],
                        "source_type": progress["source_type"],
                        "file_name": progress["file_name"],
                        "reason": reason,
                    },
                )
            else:
                self.logger.info(
                    f"⚠ Falling back to default chunking for {progress['file_name']}: {reason}"
                )
