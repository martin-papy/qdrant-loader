from __future__ import annotations

import re
from typing import Any

from ...components.search_result_models import HybridSearchResult


def build_document_lookup(
    documents: list[HybridSearchResult],
    robust: bool = False,
    logger: Any | None = None,
) -> dict[str, HybridSearchResult]:
    """Build a multi-key lookup for `HybridSearchResult` documents.

    Keys include composite `source_type:source_title`, `document_id` when present,
    and `source_title`. When `robust` is True, missing values are tolerated and a
    sanitized composite key is also added.
    """
    lookup: dict[str, HybridSearchResult] = {}

    def _normalize_key(value: Any) -> str | None:
        if value is None:
            return None
        try:
            text = str(value)
        except Exception:
            return None
        text = text.strip()
        return text if text else None

    def _set_key(key: str | None, new_doc: HybridSearchResult) -> None:
        if key is None:
            return
        existing = lookup.get(key)
        if existing is None:
            lookup[key] = new_doc
            return
        # Prevent silent overwrite: keep existing, warn about conflict
        if existing is not new_doc and logger is not None:
            try:
                logger.warning(
                    "Duplicate key detected in document lookup; keeping existing",
                    extra={
                        "key": key,
                        "existing_document_id": str(
                            getattr(existing, "document_id", "")
                        ),
                        "new_document_id": str(getattr(new_doc, "document_id", "")),
                    },
                )
            except Exception:
                pass

    for doc in documents:
        # Validate item type
        if not isinstance(doc, HybridSearchResult):
            if logger is not None:
                try:
                    logger.warning(
                        "Skipping non-HybridSearchResult in build_document_lookup"
                    )
                except Exception:
                    pass
            continue

        source_type = doc.source_type or ("unknown" if robust else None)
        source_title = doc.source_title or ("" if robust else None)

        # Primary lookup by composite key when both parts are present
        if source_type is not None and source_title is not None:
            composite_key = f"{source_type}:{source_title}"
            # Preserve original composite key verbatim (may include spaces)
            _set_key(composite_key, doc)

        # Secondary lookup by document_id if available
        if getattr(doc, "document_id", None):
            _set_key(_normalize_key(doc.document_id), doc)

        # Tertiary lookup by source_title only (fallback)
        if source_title:
            _set_key(_normalize_key(source_title), doc)

        # Quaternary lookup: sanitized composite key (robust mode only)
        if robust and isinstance(source_type, str) and isinstance(source_title, str):
            sanitized_key = f"{source_type.strip()}:{source_title.strip()}"
            normalized_sanitized = _normalize_key(sanitized_key)
            if normalized_sanitized and normalized_sanitized not in lookup:
                lookup[normalized_sanitized] = doc

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
    doc_lookup: dict[str, HybridSearchResult],
    logger: Any | None = None,
) -> HybridSearchResult | None:
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

    # Normalization helpers
    def _normalize_for_match(value: str) -> str:
        text = value.strip().lower()
        # Standardize common separators to a single space
        text = re.sub(r"[\s:_\-]+", " ", text)
        return text

    normalized_query = _normalize_for_match(doc_id)

    # Exact match on normalized keys
    for lookup_key, doc in doc_lookup.items():
        if _normalize_for_match(lookup_key) == normalized_query:
            return doc

    # Delimiter/word-boundary aware partial matching
    # Build a regex that matches the normalized query as a whole token
    if normalized_query:
        token_pattern = re.compile(
            rf"(^|\b|[\s:_\-]){re.escape(normalized_query)}($|\b|[\s:_\-])"
        )
        for lookup_key, doc in doc_lookup.items():
            normalized_key = _normalize_for_match(lookup_key)
            if token_pattern.search(normalized_key):
                if logger is not None:
                    try:
                        logger.debug(
                            f"Found document via boundary-aware match: {doc_id} -> {lookup_key}"
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
