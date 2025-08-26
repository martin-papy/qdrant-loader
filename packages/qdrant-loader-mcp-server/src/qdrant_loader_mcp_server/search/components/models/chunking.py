from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ChunkingContext:
    chunk_index: int | None = None
    total_chunks: int | None = None
    chunking_strategy: str | None = None
