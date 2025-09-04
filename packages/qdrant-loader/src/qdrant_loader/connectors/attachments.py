from __future__ import annotations

from typing import Any

from qdrant_loader.core.attachment_downloader import AttachmentMetadata


def attachment_metadata_from_dict(
    data: dict[str, Any], parent_document_id: str
) -> AttachmentMetadata:
    """Create AttachmentMetadata from a simple dict structure with input validation.

    Required keys: id, download_url.
    Optional keys: filename, size, mime_type, created_at, updated_at, author.
    Missing optional keys default to sensible values.
    """
    # Validate required fields: id and download_url
    raw_id = data.get("id", "")
    attachment_id = str(raw_id).strip()
    if not attachment_id:
        raise ValueError("Attachment 'id' is required and cannot be empty.")

    raw_url = data.get("download_url", "")
    download_url = str(raw_url).strip()
    if not download_url:
        raise ValueError("Attachment 'download_url' is required and cannot be empty.")

    # Optional fields with safe conversions/defaults
    # Ensure None becomes default and whitespace is trimmed
    filename = (data.get("filename") or "").strip() or "unknown"
    mime_type = (data.get("mime_type") or "").strip() or "application/octet-stream"

    # Safely coerce size to int
    size_value = data.get("size", 0)
    try:
        size_int = int(size_value) if size_value not in (None, "") else 0
    except Exception:
        size_int = 0
    if size_int < 0:
        size_int = 0

    return AttachmentMetadata(
        id=attachment_id,
        filename=filename,
        size=size_int,
        mime_type=mime_type,
        download_url=download_url,
        parent_document_id=parent_document_id,
        created_at=data.get("created_at"),
        updated_at=data.get("updated_at"),
        author=data.get("author"),
    )
