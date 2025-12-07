"""SharePoint-specific metadata extraction.

This module extracts metadata from SharePoint Graph API responses.

IMPORTANT: Content analysis (word_count, has_code_blocks, has_images, etc.)
is handled by the chunking strategy. This extractor focuses ONLY on
SharePoint API metadata that cannot be derived from content alone.

Fields handled by chunking strategy (DO NOT duplicate):
- word_count, line_count, char_count
- has_code_blocks, has_images, has_links, has_tables
- has_toc, heading_levels, sections_count
- estimated_read_time, paragraph_count
"""

from typing import Any

from qdrant_loader.connectors.sharepoint.config import SharePointConfig
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class SharePointMetadataExtractor:
    """Extract SharePoint-specific metadata from Graph API responses.

    NOTE: This extractor focuses ONLY on metadata from SharePoint API.
    Content analysis is handled by the chunking strategy.
    """

    def __init__(self, config: SharePointConfig):
        """Initialize the SharePoint metadata extractor.

        Args:
            config: SharePoint configuration
        """
        self.config = config

    def extract_metadata(
        self,
        file_props: dict,
        drive_name: str,
        path: str,
    ) -> dict[str, Any]:
        """Extract SharePoint-specific metadata from Graph API response.

        Args:
            file_props: File properties from SharePoint Graph API
            drive_name: Document library name
            path: File path relative to library root

        Returns:
            Dict with SharePoint-specific metadata (15 fields)
        """
        name = file_props.get("name", "")
        logger.debug(f"Extracting metadata for: {name}")

        # Get creator/modifier info from Graph API
        # These may be dict or IdentitySet objects - use safe extraction
        created_by = file_props.get("createdBy", {})
        modified_by = file_props.get("lastModifiedBy", {})

        # Extract user info safely from either dict or IdentitySet object
        created_user = self._extract_user_info(created_by)
        modified_user = self._extract_user_info(modified_by)

        return {
            # Source identification
            "source_type": "sharepoint",
            "source": self.config.source,

            # File info (basic - NOT content analysis)
            "file_name": name,
            "file_type": self._get_extension(name),
            "file_size": file_props.get("size", 0),

            # Location
            "library_name": drive_name,
            "file_path": f"{drive_name}/{path}",
            "file_directory": path.rsplit("/", 1)[0] if "/" in path else "",

            # SharePoint URLs
            "web_url": file_props.get("webUrl", ""),
            "site_url": str(self.config.site_url),

            # Author info (SharePoint-specific)
            "author": created_user.get("displayName", ""),
            "author_email": created_user.get("email", ""),
            "modified_by": modified_user.get("displayName", ""),

            # Timestamps
            "created_at": file_props.get("createdDateTime"),
            "modified_at": file_props.get("lastModifiedDateTime"),

            # SharePoint identifiers
            "item_id": file_props.get("id"),
        }

    def _extract_user_info(self, identity_set) -> dict:
        """Extract user info from IdentitySet or dict object.

        Graph API may return IdentitySet objects instead of plain dicts.
        This method handles both cases safely.

        Args:
            identity_set: Either a dict or IdentitySet object

        Returns:
            Dict with displayName and email keys
        """
        if identity_set is None:
            return {}

        # Try dict-like access first
        if isinstance(identity_set, dict):
            user = identity_set.get("user", {})
            if isinstance(user, dict):
                return user
            # User might also be an object
            return {
                "displayName": getattr(user, "display_name", None)
                or getattr(user, "displayName", ""),
                "email": getattr(user, "email", ""),
            }

        # Handle IdentitySet object from office365 library
        # IdentitySet has properties: user, application, device
        try:
            user = getattr(identity_set, "user", None)
            if user is None:
                return {}

            # User object may have display_name or displayName
            return {
                "displayName": getattr(user, "display_name", None)
                or getattr(user, "displayName", "")
                or getattr(user, "properties", {}).get("displayName", ""),
                "email": getattr(user, "email", None)
                or getattr(user, "mail", "")
                or getattr(user, "properties", {}).get("email", ""),
            }
        except Exception as e:
            logger.debug(f"Could not extract user info: {e}")
            return {}

    def _get_extension(self, filename: str) -> str:
        """Get file extension with leading dot.

        Args:
            filename: File name

        Returns:
            Extension with dot (e.g., ".pdf") or empty string
        """
        if "." not in filename:
            return ""
        return "." + filename.rsplit(".", 1)[-1].lower()

    def get_content_type(self, mime_type: str, filename: str) -> str:
        """Determine content type from mime_type or filename extension.

        Args:
            mime_type: MIME type from SharePoint (optional)
            filename: File name

        Returns:
            Content type string for Document
        """
        # Common content type mappings
        mime_to_content = {
            "text/plain": "text",
            "text/markdown": "markdown",
            "text/html": "html",
            "application/json": "json",
            "application/pdf": "pdf",
            "application/msword": "document",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "document",
            "application/vnd.ms-excel": "spreadsheet",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "spreadsheet",
            "application/vnd.ms-powerpoint": "presentation",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation": "presentation",
            "image/jpeg": "image",
            "image/png": "image",
            "image/gif": "image",
        }

        if mime_type and mime_type in mime_to_content:
            return mime_to_content[mime_type]

        # Fallback to extension
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        ext_to_content = {
            "txt": "text",
            "md": "markdown",
            "html": "html",
            "htm": "html",
            "json": "json",
            "pdf": "pdf",
            "doc": "document",
            "docx": "document",
            "xls": "spreadsheet",
            "xlsx": "spreadsheet",
            "ppt": "presentation",
            "pptx": "presentation",
            "jpg": "image",
            "jpeg": "image",
            "png": "image",
            "gif": "image",
        }

        return ext_to_content.get(ext, "binary")
