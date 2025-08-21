from __future__ import annotations

import hashlib
import json
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

    payload = json.dumps({k: v for k, v in candidate_fields.items() if v is not None}, sort_keys=True, ensure_ascii=False)
    short_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:10]
    return f"{source_type}:{source_title}:{short_hash}"


