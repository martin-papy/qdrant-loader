from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SectionInfo:
    section_title: str | None = None
    section_type: str | None = None
    section_level: int | None = None
    section_anchor: str | None = None
    section_breadcrumb: str | None = None
    section_depth: int | None = None
