from __future__ import annotations

from typing import Dict, List

from ....search.components.search_result_models import HybridSearchResult


def organize_by_hierarchy(
    results: List[HybridSearchResult],
) -> Dict[str, List[HybridSearchResult]]:
    hierarchy_groups: Dict[str, List[HybridSearchResult]] = {}
    for result in results:
        file_path_val = getattr(result, "file_path", None)
        if result.source_type == "localfile" and file_path_val:
            path_parts = [p for p in file_path_val.split("/") if p]
            root_title = path_parts[0] if path_parts else "Root"
        elif result.breadcrumb_text:
            breadcrumb_parts = result.breadcrumb_text.split(" > ")
            root_title = breadcrumb_parts[0] if breadcrumb_parts else result.source_title
        else:
            root_title = result.source_title

        if root_title not in hierarchy_groups:
            hierarchy_groups[root_title] = []
        hierarchy_groups[root_title].append(result)

    for group in hierarchy_groups.values():
        def sort_key(x):
            x_file_path = getattr(x, "file_path", None)
            if x.source_type == "localfile" and x_file_path:
                folder_depth = len([p for p in x_file_path.split("/") if p]) - 1
                return (folder_depth, x.source_title)
            else:
                return (x.depth or 0, x.source_title)

        group.sort(key=sort_key)

    return hierarchy_groups


