from __future__ import annotations

from typing import Any, Dict, Optional

from ...components.search_result_models import HybridSearchResult


def build_document_lookup(
    documents: list[HybridSearchResult],
    robust: bool = False,
    logger: Any | None = None,
) -> Dict[str, HybridSearchResult]:
    """Build a multi-key lookup for `HybridSearchResult` documents.

    Keys include composite `source_type:source_title`, `document_id` when present,
    and `source_title`. When `robust` is True, missing values are tolerated and a
    sanitized composite key is also added.
    """
    lookup: Dict[str, HybridSearchResult] = {}

    for doc in documents:
        source_type = doc.source_type or ("unknown" if robust else None)
        source_title = doc.source_title or ("" if robust else None)

        # Primary lookup by composite key when both parts are present
        if source_type is not None and source_title is not None:
            composite_key = f"{source_type}:{source_title}"
            lookup[composite_key] = doc

        # Secondary lookup by document_id if available
        if getattr(doc, "document_id", None):
            lookup[doc.document_id] = doc

        # Tertiary lookup by source_title only (fallback)
        if source_title:
            lookup[source_title] = doc

        # Quaternary lookup: sanitized composite key (robust mode only)
        if robust and isinstance(source_type, str) and isinstance(source_title, str):
            sanitized_key = f"{source_type.strip()}:{source_title.strip()}"
            if sanitized_key and sanitized_key not in lookup:
                lookup[sanitized_key] = doc

    if logger is not None:
        try:
            logger.debug(
                f"Built{' robust' if robust else ''} document lookup with {len(lookup)} keys for {len(documents)} documents"
            )
        except Exception:
            pass

    return lookup


def find_document_by_id(
    doc_id: str,
    doc_lookup: Dict[str, HybridSearchResult],
    logger: Any | None = None,
) -> Optional[HybridSearchResult]:
    """Find a document by ID using multiple lookup strategies.

    Attempts direct, sanitized, partial, and title-based matches.
    """
    if not doc_id:
        return None

    # Direct lookup
    if doc_id in doc_lookup:
        return doc_lookup[doc_id]

    # Try sanitized lookup
    sanitized_id = doc_id.strip()
    if sanitized_id in doc_lookup:
        return doc_lookup[sanitized_id]

    # Partial matching for edge cases
    for lookup_key, doc in doc_lookup.items():
        if doc_id in lookup_key or lookup_key in doc_id:
            if logger is not None:
                try:
                    logger.debug(
                        f"Found document via partial match: {doc_id} -> {lookup_key}"
                    )
                except Exception:
                    pass
            return doc

    # Try by source title extraction (handle composite keys)
    if ":" in doc_id:
        title_part = doc_id.split(":", 1)[1]
        if title_part in doc_lookup:
            return doc_lookup[title_part]

    return None


