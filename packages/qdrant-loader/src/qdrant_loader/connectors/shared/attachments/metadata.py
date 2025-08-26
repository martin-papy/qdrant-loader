from __future__ import annotations

from typing import Any

from qdrant_loader.core.attachment_downloader import AttachmentMetadata


def normalize_attachment_metadata(meta: dict, *, parent_id: str) -> AttachmentMetadata:
    """Normalize provider-agnostic metadata to `AttachmentMetadata`.

    Minimal helper for shared usage; connectors can implement richer adapters.
    """
    # Extract fields without coercing None to string
    raw_id = meta.get("id") or meta.get("attachment_id")
    attachment_id = str(raw_id) if raw_id is not None else None

    download_raw = meta.get("download_url") or meta.get("content")
    download_url = str(download_raw) if download_raw is not None else None

    metadata = AttachmentMetadata(
        id=attachment_id if attachment_id is not None else "None",
        filename=meta.get("filename") or meta.get("name") or "unknown",
        size=int(meta.get("size") or 0),
        mime_type=meta.get("mime_type")
        or meta.get("contentType")
        or "application/octet-stream",
        download_url=download_url if download_url is not None else "None",
        parent_document_id=parent_id,
        created_at=meta.get("created") or meta.get("created_at"),
        updated_at=meta.get("updated") or meta.get("updated_at"),
        author=(meta.get("author") or meta.get("creator")),
    )

    # Post-construction validation for required fields
    if not metadata.id or metadata.id == "None":
        raise ValueError("Attachment ID is required")
    if not metadata.download_url or metadata.download_url == "None":
        raise ValueError("Attachment download_url is required")

    return metadata


def jira_attachment_to_metadata(att: Any, *, parent_id: str) -> AttachmentMetadata:
    """Convert a JiraAttachment-like object to AttachmentMetadata."""
    created = getattr(att, "created", None)
    author = getattr(att, "author", None)
    return AttachmentMetadata(
        id=str(att.id),
        filename=str(att.filename),
        size=int(att.size),
        mime_type=str(att.mime_type),
        download_url=str(att.content_url),
        parent_document_id=parent_id,
        created_at=created.isoformat() if created is not None else None,
        updated_at=None,
        author=getattr(author, "display_name", None) if author is not None else None,
    )


def confluence_attachment_to_metadata(
    attachment_data: dict,
    *,
    base_url: str,
    parent_id: str,
) -> AttachmentMetadata | None:
    """Convert raw Confluence attachment JSON to AttachmentMetadata.

    Returns None if a valid download URL cannot be determined.
    """
    try:
        attachment_id = attachment_data.get("id")
        filename = attachment_data.get("title", "unknown")

        # File size from metadata or extensions
        metadata = attachment_data.get("metadata", {})
        file_size = 0
        if "mediaType" in metadata:
            file_size = metadata.get("mediaType", {}).get("size", 0)
        elif "properties" in metadata:
            file_size = metadata.get("properties", {}).get("size", 0)
        if file_size == 0:
            extensions = attachment_data.get("extensions", {})
            file_size = extensions.get("fileSize", 0)

        # MIME type from metadata or extensions
        mime_type = "application/octet-stream"
        if "mediaType" in metadata:
            mime_type = metadata.get("mediaType", {}).get("name", mime_type)
        elif "properties" in metadata:
            mime_type = metadata.get("properties", {}).get("mediaType", mime_type)
        if mime_type == "application/octet-stream":
            extensions = attachment_data.get("extensions", {})
            mime_type = extensions.get("mediaType", mime_type)

        # Download URL construction
        download_link = attachment_data.get("_links", {}).get("download")
        if not download_link:
            return None
        if str(download_link).startswith("http"):
            download_url = download_link
        elif str(download_link).startswith("/"):
            download_url = f"{base_url}{download_link}"
        else:
            download_url = f"{base_url}/rest/api/{download_link}"

        # Author and timestamps
        version = attachment_data.get("version", {})
        history = attachment_data.get("history", {})

        author = None
        if "by" in version:
            author = version.get("by", {}).get("displayName")
        elif "createdBy" in history:
            author = history.get("createdBy", {}).get("displayName")

        created_at = None
        if "createdDate" in history:
            created_at = history.get("createdDate")
        elif "created" in attachment_data:
            created_at = attachment_data.get("created")

        updated_at = None
        if "when" in version:
            updated_at = version.get("when")
        elif "lastModified" in history:
            updated_at = history.get("lastModified")

        return AttachmentMetadata(
            id=attachment_id,
            filename=filename,
            size=file_size,
            mime_type=mime_type,
            download_url=download_url,
            parent_document_id=parent_id,
            created_at=created_at,
            updated_at=updated_at,
            author=author,
        )
    except Exception:
        return None
