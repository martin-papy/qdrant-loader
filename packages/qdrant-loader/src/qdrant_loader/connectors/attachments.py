from __future__ import annotations

from typing import Any, Dict

from qdrant_loader.core.attachment_downloader import AttachmentMetadata


def attachment_metadata_from_dict(data: Dict[str, Any], parent_document_id: str) -> AttachmentMetadata:
    """Create AttachmentMetadata from a simple dict structure.

    Expected keys: id, filename, size, mime_type, download_url, created_at, updated_at, author.
    Missing optional keys default to None/0.
    """
    return AttachmentMetadata(
        id=str(data.get("id", "")),
        filename=str(data.get("filename", "unknown")),
        size=int(data.get("size", 0) or 0),
        mime_type=str(data.get("mime_type", "application/octet-stream")),
        download_url=str(data.get("download_url", "")),
        parent_document_id=parent_document_id,
        created_at=data.get("created_at"),
        updated_at=data.get("updated_at"),
        author=data.get("author"),
    )


