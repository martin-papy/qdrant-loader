from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ContentAnalysis:
    has_code_blocks: bool = False
    has_tables: bool = False
    has_images: bool = False
    has_links: bool = False
    word_count: int | None = None
    char_count: int | None = None
    estimated_read_time: int | None = None
    paragraph_count: int | None = None
