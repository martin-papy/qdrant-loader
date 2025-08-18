from __future__ import annotations

from typing import Any, Iterable, List, Set


class ResultDeduplicator:
    """Remove duplicate results based on a stable key function."""

    def __init__(self, key_attr: str = "id"):
        self.key_attr = key_attr

    def deduplicate(self, results: Iterable[Any]) -> List[Any]:
        seen: Set[str] = set()
        unique: List[Any] = []
        for item in results:
            key = getattr(item, self.key_attr, None)
            if key is None:
                unique.append(item)
                continue
            if key not in seen:
                seen.add(key)
                unique.append(item)
        return unique


