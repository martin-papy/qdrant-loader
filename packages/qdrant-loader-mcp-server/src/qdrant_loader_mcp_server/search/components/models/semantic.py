from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SemanticAnalysis:
    entities: list[dict | str] = field(default_factory=list)
    topics: list[dict | str] = field(default_factory=list)
    key_phrases: list[dict | str] = field(default_factory=list)
    pos_tags: list[dict] = field(default_factory=list)
