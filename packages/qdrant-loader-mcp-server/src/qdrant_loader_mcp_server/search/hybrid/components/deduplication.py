from __future__ import annotations

from typing import Any, Hashable, Iterable, List, Set, Mapping
import json


class ResultDeduplicator:
    """Remove duplicate results based on a stable key function."""

    def __init__(self, key_attr: str = "id"):
        self.key_attr = key_attr

    def deduplicate(self, results: Iterable[Any]) -> List[Any]:
        seen: Set[Hashable] = set()
        unique: List[Any] = []
        for item in results:
            # Support both Mapping (dict-like) and object attributes
            if isinstance(item, Mapping):
                key_obj = item.get(self.key_attr, None)
            else:
                key_obj = getattr(item, self.key_attr, None)
            if key_obj is None:
                unique.append(item)
                continue
            # Ensure the key used for set membership is hashable; fallback to string
            key: Hashable
            try:
                hash(key_obj)
                key = key_obj  # type: ignore[assignment]
            except TypeError:
                # Deterministic serialization for unhashable keys
                try:
                    key = json.dumps(key_obj, sort_keys=True, default=str)
                except Exception:
                    # Fall back to a stable string representation
                    key = repr(key_obj)
            if key not in seen:
                seen.add(key)
                unique.append(item)
        return unique


