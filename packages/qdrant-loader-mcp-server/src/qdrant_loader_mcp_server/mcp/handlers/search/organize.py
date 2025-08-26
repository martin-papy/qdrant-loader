from __future__ import annotations

import re

from ....search.components.models.hybrid import HybridSearchResult


def organize_by_hierarchy(
    results: list[HybridSearchResult],
) -> dict[str, list[HybridSearchResult]]:
    hierarchy_groups: dict[str, list[HybridSearchResult]] = {}
    for result in results:
        file_path_val = getattr(result, "file_path", None)
        breadcrumb_text_val = getattr(result, "breadcrumb_text", None)
        source_title_val = getattr(result, "source_title", None)

        if getattr(result, "source_type", None) == "localfile" and file_path_val:
            path_parts = [p for p in re.split(r"[\\/]", str(file_path_val)) if p]
            root_title = path_parts[0] if path_parts else "Root"
        elif breadcrumb_text_val:
            breadcrumb_parts = str(breadcrumb_text_val).split(" > ")
            root_title = (
                breadcrumb_parts[0]
                if breadcrumb_parts
                else (source_title_val or "Root")
            )
        else:
            root_title = source_title_val or "Root"

        if root_title not in hierarchy_groups:
            hierarchy_groups[root_title] = []
        hierarchy_groups[root_title].append(result)

    for group in hierarchy_groups.values():

        def sort_key(x):
            x_file_path = getattr(x, "file_path", None)
            x_source_title = getattr(x, "source_title", None) or ""
            if getattr(x, "source_type", None) == "localfile" and x_file_path:
                folder_depth = (
                    len([p for p in re.split(r"[\\/]", str(x_file_path)) if p]) - 1
                )
                return (folder_depth, x_source_title)
            else:
                return (getattr(x, "depth", 0) or 0, x_source_title)

        group.sort(key=sort_key)

    return hierarchy_groups
