from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class NavigationContext:
    previous_section: str | None = None
    next_section: str | None = None
    sibling_sections: list[str] = field(default_factory=list)
    subsections: list[str] = field(default_factory=list)
    document_hierarchy: list[str] = field(default_factory=list)
