from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any


def get_field(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def get_or_create_document_id(doc: Any) -> str:
    explicit_id = get_field(doc, "document_id", None)
    if explicit_id is not None:
        explicit_id_str = str(explicit_id).strip()
        if explicit_id_str:
            return explicit_id_str

    raw_source_type = get_field(doc, "source_type", "unknown")
    raw_source_title = get_field(doc, "source_title", "unknown")

    source_type = str(raw_source_type or "unknown").replace(":", "-")
    source_title = str(raw_source_title or "unknown").replace(":", "-")

    candidate_fields = {
        "title": get_field(doc, "title", None),
        "source_type": source_type,
        "source_title": source_title,
        "source_url": get_field(doc, "source_url", None),
        "file_path": get_field(doc, "file_path", None),
        "repo_name": get_field(doc, "repo_name", None),
        "parent_id": get_field(doc, "parent_id", None),
        "original_filename": get_field(doc, "original_filename", None),
        "id": get_field(doc, "id", None),
    }

    def _to_stable_primitive(value: Any) -> Any:
        # None and basic primitives
        if value is None or isinstance(value, str | int | float | bool):
            return value
        # datetime/date
        if isinstance(value, datetime | date):
            return value.isoformat()
        # bytes/bytearray
        if isinstance(value, bytes | bytearray):
            try:
                return value.decode("utf-8")
            except Exception:
                return value.decode("utf-8", errors="replace")
        # Path
        if isinstance(value, Path):
            return str(value)
        # Enum
        if isinstance(value, Enum):
            return value.value  # type: ignore[return-value]
        # Mapping
        if isinstance(value, Mapping):
            # Convert keys to str and recurse on values; sort by key for determinism
            converted_items = (
                (str(k), _to_stable_primitive(v)) for k, v in value.items()
            )
            sorted_items = sorted(converted_items, key=lambda kv: kv[0])
            return dict(sorted_items)
        # Iterables (list/tuple/set etc.), but not strings/bytes (already handled)
        if isinstance(value, Iterable):
            converted_list = [_to_stable_primitive(v) for v in value]
            # For sets or unordered iterables, sort deterministically by JSON representation
            try:
                return sorted(
                    converted_list,
                    key=lambda x: json.dumps(x, sort_keys=True, ensure_ascii=False),
                )
            except Exception:
                return converted_list
        # Fallback to string representation for anything else
        return str(value)

    stable_fields = {
        k: _to_stable_primitive(v) for k, v in candidate_fields.items() if v is not None
    }

    payload = json.dumps(
        stable_fields,
        sort_keys=True,
        ensure_ascii=False,
    )
    short_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:10]
    return f"{source_type}:{source_title}:{short_hash}"
