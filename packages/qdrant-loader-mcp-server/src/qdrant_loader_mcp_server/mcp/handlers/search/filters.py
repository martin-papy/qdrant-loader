from __future__ import annotations

import os
from typing import Any

from ....mcp.formatters.utils import FormatterUtils
from ....search.components.search_result_models import HybridSearchResult


def apply_hierarchy_filters(
    results: list[HybridSearchResult], hierarchy_filter: dict[str, Any]
) -> list[HybridSearchResult]:
    filtered_results = []
    for result in results:
        if result.source_type not in ["confluence", "localfile"]:
            continue
        if "depth" in hierarchy_filter:
            file_path_val = getattr(result, "file_path", None)
            if result.source_type == "localfile" and file_path_val:
                path_parts = [p for p in file_path_val.split("/") if p]
                folder_depth = max(0, len(path_parts) - 2)
                if folder_depth != hierarchy_filter["depth"]:
                    continue
            elif hasattr(result, "depth") and result.depth != hierarchy_filter["depth"]:
                continue
        if "parent_title" in hierarchy_filter:
            expected_parent = hierarchy_filter["parent_title"]
            if result.source_type == "localfile":
                file_path_val = getattr(result, "file_path", None)
                if file_path_val:
                    path_parts = [p for p in file_path_val.split("/") if p]
                    parent_folder = path_parts[-2] if len(path_parts) > 1 else ""
                    if parent_folder != expected_parent:
                        continue
                else:
                    continue
            else:
                parent_title_val = getattr(result, "parent_title", None)
                if parent_title_val != expected_parent:
                    continue
        if hierarchy_filter.get("root_only", False):
            if not result.is_root_document():
                continue
        if "has_children" in hierarchy_filter and result.source_type != "localfile":
            if result.has_children() != hierarchy_filter["has_children"]:
                continue
        filtered_results.append(result)
    return filtered_results


def apply_attachment_filters(
    results: list[HybridSearchResult], attachment_filter: dict[str, Any]
) -> list[HybridSearchResult]:
    filtered_results = []
    for result in results:
        if result.source_type != "confluence":
            continue
        if "attachments_only" in attachment_filter and not result.is_attachment:
            continue
        if "parent_document_title" in attachment_filter:
            if (
                result.parent_document_title
                != attachment_filter["parent_document_title"]
            ):
                continue
        if "file_type" in attachment_filter:
            result_file_type = result.get_file_type()
            if result_file_type != attachment_filter["file_type"]:
                continue
        _min_size = attachment_filter.get("file_size_min")
        if (
            _min_size is not None
            and result.file_size is not None
            and result.file_size < _min_size
        ):
            continue
        _max_size = attachment_filter.get("file_size_max")
        if (
            _max_size is not None
            and result.file_size is not None
            and result.file_size > _max_size
        ):
            continue
        if "author" in attachment_filter:
            if result.attachment_author != attachment_filter["author"]:
                continue
        filtered_results.append(result)
    return filtered_results


def apply_lightweight_attachment_filters(
    results: list[HybridSearchResult],
    attachment_filter: dict[str, Any],
    file_type_extractor: Any | None = None,
) -> list[HybridSearchResult]:
    filtered_results = []
    for result in results:
        _is_attachment_flag = bool(getattr(result, "is_attachment", False))
        _original_filename = getattr(result, "original_filename", None)
        _file_path = getattr(result, "file_path", None)
        _is_path_file = False
        if isinstance(_file_path, str) and not _file_path.endswith("/"):
            _basename = os.path.basename(_file_path)
            _is_path_file = "." in _basename
        is_attachment = _is_attachment_flag or bool(_original_filename) or _is_path_file
        if not is_attachment:
            continue
        if attachment_filter.get("attachments_only") and not bool(
            getattr(result, "is_attachment", False)
        ):
            continue
        if attachment_filter.get("file_type"):
            if file_type_extractor is not None:
                file_type = file_type_extractor(result)
            else:
                file_type = FormatterUtils.extract_file_type_minimal(result)
            if file_type != attachment_filter["file_type"]:
                continue
        _file_size = getattr(result, "file_size", None)
        if (
            attachment_filter.get("file_size_min") is not None
            and _file_size is not None
            and _file_size < attachment_filter["file_size_min"]
        ):
            continue
        if (
            attachment_filter.get("file_size_max") is not None
            and _file_size is not None
            and _file_size > attachment_filter["file_size_max"]
        ):
            continue
        if attachment_filter.get("parent_document_title"):
            parent_title = getattr(result, "parent_document_title", None) or getattr(
                result, "parent_title", None
            )
            if parent_title != attachment_filter["parent_document_title"]:
                continue
        if attachment_filter.get("author"):
            author = getattr(result, "attachment_author", None) or getattr(
                result, "author", None
            )
            if author != attachment_filter["author"]:
                continue
        filtered_results.append(result)
    return filtered_results
