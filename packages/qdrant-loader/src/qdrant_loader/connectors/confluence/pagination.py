from __future__ import annotations

import re
from typing import Any

_ALLOWED_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _quote_cql_literal(value: str) -> str:
    # Escape backslashes first, then double quotes
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _sanitize_space_key(space_key: str) -> str:
    if not _ALLOWED_TOKEN_RE.fullmatch(space_key):
        raise ValueError(
            "Invalid Confluence space key. Only alphanumerics, underscore and hyphen are allowed."
        )
    return _quote_cql_literal(space_key)


def _sanitize_content_types(content_types: list[str]) -> list[str]:
    sanitized: list[str] = []
    for content_type in content_types:
        if not isinstance(content_type, str) or not _ALLOWED_TOKEN_RE.fullmatch(
            content_type
        ):
            raise ValueError(f"Invalid Confluence content type: {content_type!r}")
        sanitized.append(_quote_cql_literal(content_type))
    return sanitized


def build_cloud_search_params(
    space_key: str, content_types: list[str] | None, cursor: str | None
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "expand": "body.storage,version,metadata.labels,history,space,extensions.position,children.comment.body.storage,ancestors,children.page",
        "limit": 25,
    }
    cql = f"space = {_sanitize_space_key(space_key)}"
    if content_types:
        safe_types = _sanitize_content_types(content_types)
        cql += f" and type in ({','.join(safe_types)})"
    params["cql"] = cql
    if cursor is not None:
        params["cursor"] = cursor
    return params


def build_dc_search_params(
    space_key: str, content_types: list[str] | None, start: int
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "expand": "body.storage,version,metadata.labels,history,space,extensions.position,children.comment.body.storage,ancestors,children.page",
        "limit": 25,
        "start": start,
    }
    cql = f"space = {_sanitize_space_key(space_key)}"
    if content_types:
        safe_types = _sanitize_content_types(content_types)
        cql += f" and type in ({','.join(safe_types)})"
    params["cql"] = cql
    return params
