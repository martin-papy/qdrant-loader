from __future__ import annotations

from typing import Any


def extract_hierarchy_info(content: dict[str, Any]) -> dict[str, Any]:
    hierarchy_info = {
        "ancestors": [],
        "parent_id": None,
        "parent_title": None,
        "children": [],
        "depth": 0,
        "breadcrumb": [],
    }

    ancestors = content.get("ancestors", [])
    if ancestors:
        ancestor_chain = []
        breadcrumb = []
        for ancestor in ancestors:
            ancestor_info = {
                "id": ancestor.get("id"),
                "title": ancestor.get("title"),
                "type": ancestor.get("type", "page"),
            }
            ancestor_chain.append(ancestor_info)
            breadcrumb.append(ancestor.get("title", "Unknown"))
        hierarchy_info["ancestors"] = ancestor_chain
        hierarchy_info["breadcrumb"] = breadcrumb
        hierarchy_info["depth"] = len(ancestor_chain)
        if ancestor_chain:
            immediate_parent = ancestor_chain[-1]
            hierarchy_info["parent_id"] = immediate_parent["id"]
            hierarchy_info["parent_title"] = immediate_parent["title"]

    children_data = content.get("children", {})
    if "page" in children_data:
        child_pages = children_data["page"].get("results", [])
        children_info = []
        for child in child_pages:
            children_info.append(
                {
                    "id": child.get("id"),
                    "title": child.get("title"),
                    "type": child.get("type", "page"),
                }
            )
        hierarchy_info["children"] = children_info

    return hierarchy_info
