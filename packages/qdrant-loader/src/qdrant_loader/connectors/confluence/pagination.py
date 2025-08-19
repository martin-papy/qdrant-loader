from __future__ import annotations

from typing import Any, Dict, Optional


def build_cloud_search_params(space_key: str, content_types: list[str] | None, cursor: Optional[str]) -> Dict[str, Any]:
    params: Dict[str, Any] = {
        "expand": "body.storage,version,metadata.labels,history,space,extensions.position,children.comment.body.storage,ancestors,children.page",
        "limit": 25,
    }
    cql = f"space = {space_key}"
    if content_types:
        cql += f" and type in ({','.join(content_types)})"
    params["cql"] = cql
    if cursor:
        params["cursor"] = cursor
    return params


def build_dc_search_params(space_key: str, content_types: list[str] | None, start: int) -> Dict[str, Any]:
    params: Dict[str, Any] = {
        "expand": "body.storage,version,metadata.labels,history,space,extensions.position,children.comment.body.storage,ancestors,children.page",
        "limit": 25,
        "start": start,
    }
    cql = f"space = {space_key}"
    if content_types:
        cql += f" and type in ({','.join(content_types)})"
    params["cql"] = cql
    return params


