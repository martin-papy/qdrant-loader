from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CrossReferenceInfo:
    cross_references: list[dict] = field(default_factory=list)
    topic_analysis: dict | None = None
    content_type_context: str | None = None
