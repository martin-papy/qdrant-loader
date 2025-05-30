import asyncio
import re
from datetime import datetime

import requests
from requests.auth import HTTPBasicAuth

from qdrant_loader.config.types import SourceType
from qdrant_loader.connectors.base import BaseConnector
from qdrant_loader.connectors.confluence.config import (
    ConfluenceDeploymentType,
    ConfluenceSpaceConfig,
)
from qdrant_loader.core.attachment_downloader import (
    AttachmentDownloader,
    AttachmentMetadata,
)
from qdrant_loader.core.document import Document
from qdrant_loader.core.file_conversion import (
    FileConverter,
    FileDetector,
    FileConversionConfig,
    FileConversionError,
)
from qdrant_loader.utils.logging import LoggingConfig
from urllib.parse import urlparse

logger = LoggingConfig.get_logger(__name__)


class ConfluenceConnector(BaseConnector):
    """Connector for Atlassian Confluence."""

    def __init__(self, config: ConfluenceSpaceConfig):
        """Initialize the connector with configuration.

        Args:
            config: Confluence configuration
        """
        super().__init__(config)
        self.config = config
        self.base_url = config.base_url

        # Initialize session
        self.session = requests.Session()

        # Set up authentication based on deployment type
        self._setup_authentication()
        self._initialized = False

        # Initialize file conversion and attachment handling components
        self.file_converter = None
        self.file_detector = None
        self.attachment_downloader = None

        if self.config.enable_file_conversion:
            logger.info("File conversion enabled for Confluence connector")
            # File conversion config will be set from global config during ingestion
            self.file_detector = FileDetector()
        else:
            logger.debug("File conversion disabled for Confluence connector")

    def set_file_conversion_config(self, file_conversion_config: FileConversionConfig):
        """Set file conversion configuration from global config.

        Args:
            file_conversion_config: Global file conversion configuration
        """
        if self.config.enable_file_conversion:
            self.file_converter = FileConverter(file_conversion_config)

            # Initialize attachment downloader if download_attachments is enabled
            if self.config.download_attachments:
                self.attachment_downloader = AttachmentDownloader(
                    session=self.session,
                    file_conversion_config=file_conversion_config,
                    enable_file_conversion=True,
                    max_attachment_size=file_conversion_config.max_file_size,
                )
                logger.info("Attachment downloader initialized with file conversion")
            else:
                logger.debug("Attachment downloading disabled")

            logger.debug("File converter initialized with global config")

    def _setup_authentication(self):
        """Set up authentication based on deployment type."""
        if self.config.deployment_type == ConfluenceDeploymentType.CLOUD:
            # Cloud uses Basic Auth with email:api_token
            if not self.config.token:
                raise ValueError("API token is required for Confluence Cloud")
            if not self.config.email:
                raise ValueError("Email is required for Confluence Cloud")

            self.session.auth = HTTPBasicAuth(self.config.email, self.config.token)
            logger.debug(
                "Configured Confluence Cloud authentication with email and API token"
            )

        else:
            # Data Center/Server uses Personal Access Token with Bearer authentication
            if not self.config.token:
                raise ValueError(
                    "Personal Access Token is required for Confluence Data Center/Server"
                )

            self.session.headers.update(
                {
                    "Authorization": f"Bearer {self.config.token}",
                    "Content-Type": "application/json",
                }
            )
            logger.debug(
                "Configured Confluence Data Center authentication with Personal Access Token"
            )

    def _auto_detect_deployment_type(self) -> ConfluenceDeploymentType:
        """Auto-detect the Confluence deployment type based on the base URL.

        Returns:
            ConfluenceDeploymentType: Detected deployment type
        """
        try:
            parsed_url = urlparse(str(self.base_url))
            hostname = parsed_url.hostname

            if hostname is None:
                # If we can't parse the hostname, default to DATACENTER
                return ConfluenceDeploymentType.DATACENTER

            # Cloud instances use *.atlassian.net domains
            # Use proper hostname checking with endswith to ensure it's a subdomain
            if hostname.endswith(".atlassian.net") or hostname == "atlassian.net":
                return ConfluenceDeploymentType.CLOUD

            # Everything else is likely Data Center/Server
            return ConfluenceDeploymentType.DATACENTER
        except Exception:
            # If URL parsing fails, default to DATACENTER
            return ConfluenceDeploymentType.DATACENTER

    async def __aenter__(self):
        """Async context manager entry."""
        if not self._initialized:
            self._initialized = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self._initialized = False

    def _get_api_url(self, endpoint: str) -> str:
        """Construct the full API URL for an endpoint.

        Args:
            endpoint: API endpoint path

        Returns:
            str: Full API URL
        """
        return f"{self.base_url}/rest/api/{endpoint}"

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make an authenticated request to the Confluence API.

        Args:
            method: HTTP method
            endpoint: API endpoint path
            **kwargs: Additional request parameters

        Returns:
            dict: Response data

        Raises:
            requests.exceptions.RequestException: If the request fails
        """
        url = self._get_api_url(endpoint)
        try:
            # For Data Center with PAT, headers are already set
            # For Cloud or Data Center with basic auth, use session auth
            if not self.session.headers.get("Authorization"):
                kwargs["auth"] = self.session.auth

            response = await asyncio.to_thread(
                self.session.request, method, url, **kwargs
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to make request to {url}: {e}")
            # Log additional context for debugging
            logger.error(
                "Request details",
                method=method,
                url=url,
                deployment_type=self.config.deployment_type,
                has_auth_header=bool(self.session.headers.get("Authorization")),
                has_session_auth=bool(self.session.auth),
            )
            raise

    async def _get_space_content_cloud(self, cursor: str | None = None) -> dict:
        """Fetch content from a Confluence Cloud space using cursor-based pagination.

        Args:
            cursor: Cursor for pagination. If None, starts from the beginning.

        Returns:
            dict: Response containing space content
        """
        if not self.config.content_types:
            params = {
                "cql": f"space = {self.config.space_key}",
                "expand": "body.storage,version,metadata.labels,history,space,extensions.position,children.comment.body.storage,ancestors,children.page",
                "limit": 25,  # Using a reasonable default limit
            }
        else:
            params = {
                "cql": f"space = {self.config.space_key} and type in ({','.join(self.config.content_types)})",
                "expand": "body.storage,version,metadata.labels,history,space,extensions.position,children.comment.body.storage,ancestors,children.page",
                "limit": 25,  # Using a reasonable default limit
            }

        if cursor:
            params["cursor"] = cursor

        logger.debug(
            "Making Confluence Cloud API request",
            url=f"{self.base_url}/rest/api/content/search",
            params=params,
        )
        response = await self._make_request("GET", "content/search", params=params)
        if response and "results" in response:
            # For Cloud, we can't easily calculate page numbers from cursor, so just log occasionally
            if len(response["results"]) > 0:
                logger.debug(
                    f"Fetching Confluence Cloud documents: {len(response['results'])} found",
                    count=len(response["results"]),
                    total_size=response.get("totalSize", response.get("size", 0)),
                )
        return response

    async def _get_space_content_datacenter(self, start: int = 0) -> dict:
        """Fetch content from a Confluence Data Center space using start/limit pagination.

        Args:
            start: Starting index for pagination. Defaults to 0.

        Returns:
            dict: Response containing space content
        """
        if not self.config.content_types:
            params = {
                "cql": f"space = {self.config.space_key}",
                "expand": "body.storage,version,metadata.labels,history,space,extensions.position,children.comment.body.storage,ancestors,children.page",
                "limit": 25,  # Using a reasonable default limit
                "start": start,
            }
        else:
            params = {
                "cql": f"space = {self.config.space_key} and type in ({','.join(self.config.content_types)})",
                "expand": "body.storage,version,metadata.labels,history,space,extensions.position,children.comment.body.storage,ancestors,children.page",
                "limit": 25,  # Using a reasonable default limit
                "start": start,
            }

        logger.debug(
            "Making Confluence Data Center API request",
            url=f"{self.base_url}/rest/api/content/search",
            params=params,
        )
        response = await self._make_request("GET", "content/search", params=params)
        if response and "results" in response:
            # Only log every 10th page to reduce verbosity
            page_num = start // 25 + 1
            if page_num == 1 or page_num % 10 == 0:
                logger.debug(
                    f"Fetching Confluence Data Center documents (page {page_num}): {len(response['results'])} found",
                    count=len(response["results"]),
                    total_size=response.get("totalSize", response.get("size", 0)),
                    start=start,
                )
        return response

    async def _get_space_content(self, start: int = 0) -> dict:
        """Backward compatibility method for tests.

        Args:
            start: Starting index for pagination. Defaults to 0.

        Returns:
            dict: Response containing space content
        """
        if self.config.deployment_type == ConfluenceDeploymentType.CLOUD:
            # For Cloud, ignore start parameter and use cursor=None
            return await self._get_space_content_cloud(None)
        else:
            # For Data Center, use start parameter
            return await self._get_space_content_datacenter(start)

    async def _get_content_attachments(
        self, content_id: str
    ) -> list[AttachmentMetadata]:
        """Fetch attachments for a specific content item.

        Args:
            content_id: ID of the content item

        Returns:
            List of attachment metadata
        """
        if not self.config.download_attachments:
            return []

        try:
            # Fetch attachments using Confluence API
            endpoint = f"content/{content_id}/child/attachment"
            params = {
                "expand": "metadata,version,history",  # Include history for better metadata
                "limit": 50,  # Reasonable limit for attachments per page
            }

            response = await self._make_request("GET", endpoint, params=params)
            attachments = []

            for attachment_data in response.get("results", []):
                try:
                    # Extract attachment metadata
                    attachment_id = attachment_data.get("id")
                    filename = attachment_data.get("title", "unknown")

                    # Get file size and MIME type from metadata
                    # The structure can differ between Cloud and Data Center
                    metadata = attachment_data.get("metadata", {})

                    # Try different paths for file size (Cloud vs Data Center differences)
                    file_size = 0
                    if "mediaType" in metadata:
                        # Data Center format
                        file_size = metadata.get("mediaType", {}).get("size", 0)
                    elif "properties" in metadata:
                        # Alternative format in some versions
                        file_size = metadata.get("properties", {}).get("size", 0)

                    # If still no size, try from extensions
                    if file_size == 0:
                        extensions = attachment_data.get("extensions", {})
                        file_size = extensions.get("fileSize", 0)

                    # Try different paths for MIME type
                    mime_type = "application/octet-stream"  # Default fallback
                    if "mediaType" in metadata:
                        # Data Center format
                        mime_type = metadata.get("mediaType", {}).get("name", mime_type)
                    elif "properties" in metadata:
                        # Alternative format
                        mime_type = metadata.get("properties", {}).get(
                            "mediaType", mime_type
                        )

                    # If still no MIME type, try from extensions
                    if mime_type == "application/octet-stream":
                        extensions = attachment_data.get("extensions", {})
                        mime_type = extensions.get("mediaType", mime_type)

                    # Get download URL - this differs significantly between Cloud and Data Center
                    download_link = attachment_data.get("_links", {}).get("download")
                    if not download_link:
                        logger.warning(
                            "No download link found for attachment",
                            attachment_id=attachment_id,
                            filename=filename,
                            deployment_type=self.config.deployment_type,
                        )
                        continue

                    # Construct full download URL based on deployment type
                    if self.config.deployment_type == ConfluenceDeploymentType.CLOUD:
                        # Cloud URLs are typically absolute or need different handling
                        if download_link.startswith("http"):
                            download_url = download_link
                        elif download_link.startswith("/"):
                            download_url = f"{self.base_url}{download_link}"
                        else:
                            # Relative path - construct full URL
                            download_url = f"{self.base_url}/rest/api/{download_link}"
                    else:
                        # Data Center URLs
                        if download_link.startswith("http"):
                            download_url = download_link
                        elif download_link.startswith("/"):
                            download_url = f"{self.base_url}{download_link}"
                        else:
                            # Relative path - construct full URL
                            download_url = f"{self.base_url}/rest/api/{download_link}"

                    # Get author and timestamps - structure can vary between versions
                    version = attachment_data.get("version", {})
                    history = attachment_data.get("history", {})

                    # Try different paths for author information
                    author = None
                    if "by" in version:
                        # Standard version author
                        author = version.get("by", {}).get("displayName")
                    elif "createdBy" in history:
                        # History-based author (more common in Cloud)
                        author = history.get("createdBy", {}).get("displayName")

                    # Try different paths for timestamps
                    created_at = None
                    updated_at = None

                    # Creation timestamp
                    if "createdDate" in history:
                        created_at = history.get("createdDate")
                    elif "created" in attachment_data:
                        created_at = attachment_data.get("created")

                    # Update timestamp
                    if "when" in version:
                        updated_at = version.get("when")
                    elif "lastModified" in history:
                        updated_at = history.get("lastModified")

                    attachment = AttachmentMetadata(
                        id=attachment_id,
                        filename=filename,
                        size=file_size,
                        mime_type=mime_type,
                        download_url=download_url,
                        parent_document_id=content_id,
                        created_at=created_at,
                        updated_at=updated_at,
                        author=author,
                    )

                    attachments.append(attachment)

                    logger.debug(
                        "Found attachment",
                        attachment_id=attachment_id,
                        filename=filename,
                        size=file_size,
                        mime_type=mime_type,
                        deployment_type=self.config.deployment_type,
                    )

                except Exception as e:
                    logger.warning(
                        "Failed to process attachment metadata",
                        attachment_id=attachment_data.get("id"),
                        filename=attachment_data.get("title"),
                        deployment_type=self.config.deployment_type,
                        error=str(e),
                    )
                    continue

            logger.debug(
                "Found attachments for content",
                content_id=content_id,
                attachment_count=len(attachments),
                deployment_type=self.config.deployment_type,
            )

            return attachments

        except Exception as e:
            logger.error(
                "Failed to fetch attachments",
                content_id=content_id,
                deployment_type=self.config.deployment_type,
                error=str(e),
            )
            return []

    def _should_process_content(self, content: dict) -> bool:
        """Check if content should be processed based on labels.

        Args:
            content: Content metadata from Confluence API

        Returns:
            bool: True if content should be processed, False otherwise
        """
        # Get content labels
        labels = {
            label["name"]
            for label in content.get("metadata", {})
            .get("labels", {})
            .get("results", [])
        }

        # Log content details for debugging
        logger.debug(
            "Checking content for processing",
            content_id=content.get("id"),
            content_type=content.get("type"),
            title=content.get("title"),
            labels=labels,
            exclude_labels=self.config.exclude_labels,
            include_labels=self.config.include_labels,
        )

        # Check exclude labels first, if there are any specified
        if self.config.exclude_labels and any(
            label in labels for label in self.config.exclude_labels
        ):
            logger.debug(
                "Content excluded due to exclude labels",
                content_id=content.get("id"),
                title=content.get("title"),
                matching_labels=[
                    label for label in labels if label in self.config.exclude_labels
                ],
            )
            return False

        # If include labels are specified, content must have at least one
        if self.config.include_labels:
            has_include_label = any(
                label in labels for label in self.config.include_labels
            )
            if not has_include_label:
                logger.debug(
                    "Content excluded due to missing include labels",
                    content_id=content.get("id"),
                    title=content.get("title"),
                    required_labels=self.config.include_labels,
                )
            return has_include_label

        return True

    def _extract_hierarchy_info(self, content: dict) -> dict:
        """Extract page hierarchy information from Confluence content.

        Args:
            content: Content item from Confluence API

        Returns:
            dict: Hierarchy information including ancestors, parent, and children
        """
        hierarchy_info = {
            "ancestors": [],
            "parent_id": None,
            "parent_title": None,
            "children": [],
            "depth": 0,
            "breadcrumb": [],
        }

        try:
            # Extract ancestors information
            ancestors = content.get("ancestors", [])
            if ancestors:
                # Build ancestor chain (from root to immediate parent)
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

                # The last ancestor is the immediate parent
                if ancestor_chain:
                    immediate_parent = ancestor_chain[-1]
                    hierarchy_info["parent_id"] = immediate_parent["id"]
                    hierarchy_info["parent_title"] = immediate_parent["title"]

            # Extract children information (only pages, not comments)
            children_data = content.get("children", {})
            if "page" in children_data:
                child_pages = children_data["page"].get("results", [])
                children_info = []

                for child in child_pages:
                    child_info = {
                        "id": child.get("id"),
                        "title": child.get("title"),
                        "type": child.get("type", "page"),
                    }
                    children_info.append(child_info)

                hierarchy_info["children"] = children_info

            logger.debug(
                "Extracted hierarchy info",
                content_id=content.get("id"),
                content_title=content.get("title"),
                depth=hierarchy_info["depth"],
                parent_id=hierarchy_info["parent_id"],
                children_count=len(hierarchy_info["children"]),
                breadcrumb=hierarchy_info["breadcrumb"],
            )

        except Exception as e:
            logger.warning(
                "Failed to extract hierarchy information",
                content_id=content.get("id"),
                content_title=content.get("title"),
                error=str(e),
            )

        return hierarchy_info

    def _process_content(
        self, content: dict, clean_html: bool = True
    ) -> Document | None:
        """Process a single content item from Confluence.

        Args:
            content: Content item from Confluence API
            clean_html: Whether to clean HTML tags from content. Defaults to True.

        Returns:
            Document if processing successful

        Raises:
            ValueError: If required fields are missing or malformed
        """
        try:
            # Extract required fields
            content_id = content.get("id")
            title = content.get("title")
            space = content.get("space", {}).get("key")

            # Log content details for debugging
            logger.debug(
                "Processing content",
                content_id=content_id,
                title=title,
                space=space,
                type=content.get("type"),
                version=content.get("version", {}).get("number"),
                has_body=bool(content.get("body", {}).get("storage", {}).get("value")),
                comment_count=len(
                    content.get("children", {}).get("comment", {}).get("results", [])
                ),
                label_count=len(
                    content.get("metadata", {}).get("labels", {}).get("results", [])
                ),
            )

            body = content.get("body", {}).get("storage", {}).get("value")
            # Check for missing or malformed body
            if not body:
                logger.warning(
                    "Content body is missing or malformed, using title as content",
                    content_id=content_id,
                    title=title,
                    content_type=content.get("type"),
                    space=space,
                )
                # Use title as fallback content instead of failing
                body = title or f"[Empty page: {content_id}]"

            # Check for other missing required fields
            missing_fields = []
            if not content_id:
                missing_fields.append("id")
            if not title:
                missing_fields.append("title")
            if not space:
                missing_fields.append("space")

            if missing_fields:
                logger.warning(
                    "Content is missing required fields",
                    content_id=content_id,
                    title=title,
                    content_type=content.get("type"),
                    missing_fields=missing_fields,
                    space=space,
                )
                raise ValueError(
                    f"Content is missing required fields: {', '.join(missing_fields)}"
                )

            # Get version information
            version = content.get("version", {})
            version_number = (
                version.get("number", 1) if isinstance(version, dict) else 1
            )

            # Get author information with better error handling
            author = None
            try:
                author = (
                    content.get("history", {}).get("createdBy", {}).get("displayName")
                )
                if not author:
                    # Fallback to version author for Data Center
                    author = content.get("version", {}).get("by", {}).get("displayName")
            except (AttributeError, TypeError):
                logger.debug(
                    "Could not extract author information", content_id=content_id
                )

            # Get timestamps with improved parsing for both Cloud and Data Center
            created_at = None
            updated_at = None

            # Try to get creation date from history (both Cloud and Data Center)
            try:
                if "history" in content and "createdDate" in content["history"]:
                    created_at = content["history"]["createdDate"]
                elif "history" in content and "createdAt" in content["history"]:
                    # Alternative field name in some Data Center versions
                    created_at = content["history"]["createdAt"]
            except (ValueError, TypeError, KeyError):
                logger.debug("Could not parse creation date", content_id=content_id)

            # Try to get update date from version (both Cloud and Data Center)
            try:
                if "version" in content and "when" in content["version"]:
                    updated_at = content["version"]["when"]
                elif "version" in content and "friendlyWhen" in content["version"]:
                    # Some Data Center versions use friendlyWhen
                    updated_at = content["version"]["friendlyWhen"]
            except (ValueError, TypeError, KeyError):
                logger.debug("Could not parse update date", content_id=content_id)

            # Process comments
            comments = []
            if "children" in content and "comment" in content["children"]:
                for comment in content["children"]["comment"]["results"]:
                    comment_body = (
                        comment.get("body", {}).get("storage", {}).get("value", "")
                    )
                    comment_author = (
                        comment.get("history", {})
                        .get("createdBy", {})
                        .get("displayName", "")
                    )
                    comment_created = comment.get("history", {}).get("createdDate", "")
                    comments.append(
                        {
                            "body": (
                                self._clean_html(comment_body)
                                if clean_html
                                else comment_body
                            ),
                            "author": comment_author,
                            "created_at": comment_created,
                        }
                    )

            # Extract hierarchy information
            hierarchy_info = self._extract_hierarchy_info(content)

            # Create metadata with all available information including hierarchy
            metadata = {
                "id": content_id,
                "title": title,
                "space": space,
                "version": version_number,
                "type": content.get("type", "unknown"),
                "author": author,
                "labels": [
                    label["name"]
                    for label in content.get("metadata", {})
                    .get("labels", {})
                    .get("results", [])
                ],
                "comments": comments,
                "updated_at": updated_at,
                "created_at": created_at,
                # Page hierarchy information
                "hierarchy": hierarchy_info,
                "parent_id": hierarchy_info["parent_id"],
                "parent_title": hierarchy_info["parent_title"],
                "ancestors": hierarchy_info["ancestors"],
                "children": hierarchy_info["children"],
                "depth": hierarchy_info["depth"],
                "breadcrumb": hierarchy_info["breadcrumb"],
                "breadcrumb_text": (
                    " > ".join(hierarchy_info["breadcrumb"])
                    if hierarchy_info["breadcrumb"]
                    else ""
                ),
            }

            # Clean content if requested
            content_text = self._clean_html(body) if clean_html else body

            # Construct URL based on deployment type
            page_url = self._construct_page_url(
                space or "", content_id or "", content.get("type", "page")
            )

            # Parse timestamps for Document constructor
            parsed_created_at = self._parse_timestamp(created_at)
            parsed_updated_at = self._parse_timestamp(updated_at)

            # Create document with all fields properly populated
            document = Document(
                title=title,
                content=content_text,
                content_type="html",
                metadata=metadata,
                source_type=SourceType.CONFLUENCE,
                source=self.config.source,
                url=page_url,
                is_deleted=False,
                updated_at=parsed_updated_at,
                created_at=parsed_created_at,
            )

            return document

        except Exception as e:
            logger.error(
                "Failed to process content",
                content_id=content.get("id"),
                content_title=content.get("title"),
                content_type=content.get("type"),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def _construct_page_url(
        self, space: str, content_id: str, content_type: str = "page"
    ) -> str:
        """Construct the appropriate URL for a Confluence page based on deployment type.

        Args:
            space: The space key
            content_id: The content ID
            content_type: The type of content (page, blogpost, etc.)

        Returns:
            The constructed URL
        """
        if self.config.deployment_type == ConfluenceDeploymentType.CLOUD:
            # Cloud URLs use a different format
            if content_type == "blogpost":
                return f"{self.base_url}/spaces/{space}/blog/{content_id}"
            else:
                return f"{self.base_url}/spaces/{space}/pages/{content_id}"
        else:
            # Data Center/Server URLs
            if content_type == "blogpost":
                return f"{self.base_url}/display/{space}/{content_id}"
            else:
                return f"{self.base_url}/display/{space}/{content_id}"

    def _parse_timestamp(self, timestamp_str: str | None) -> "datetime | None":
        """Parse a timestamp string into a datetime object.

        Args:
            timestamp_str: The timestamp string to parse

        Returns:
            Parsed datetime object or None if parsing fails
        """
        if not timestamp_str:
            return None

        try:
            import re
            from datetime import datetime

            # Handle various timestamp formats from Confluence
            # ISO format with timezone: 2024-05-24T20:57:56.130+07:00
            if re.match(
                r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}[+-]\d{2}:\d{2}",
                timestamp_str,
            ):
                return datetime.fromisoformat(timestamp_str)

            # ISO format without microseconds: 2024-05-24T20:57:56+07:00
            elif re.match(
                r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}", timestamp_str
            ):
                return datetime.fromisoformat(timestamp_str)

            # ISO format with Z timezone: 2024-05-24T20:57:56.130Z
            elif re.match(
                r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", timestamp_str
            ):
                return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

            # ISO format without timezone: 2024-05-24T20:57:56.130
            elif re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}", timestamp_str):
                return datetime.fromisoformat(timestamp_str)

            # Fallback: try direct parsing
            else:
                return datetime.fromisoformat(timestamp_str)

        except (ValueError, TypeError, AttributeError) as e:
            logger.debug(f"Failed to parse timestamp '{timestamp_str}': {e}")
            return None

    def _clean_html(self, html: str) -> str:
        """Clean HTML content by removing tags and special characters.

        Args:
            html: HTML content to clean

        Returns:
            Cleaned text
        """
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", html)
        # Replace HTML entities
        text = text.replace("&amp;", "and")
        text = re.sub(r"&[^;]+;", " ", text)
        # Replace multiple spaces with single space
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    async def get_documents(self) -> list[Document]:
        """Fetch and process documents from Confluence.

        Returns:
            list[Document]: List of processed documents
        """
        documents = []
        page_count = 0
        total_documents = 0

        if self.config.deployment_type == ConfluenceDeploymentType.CLOUD:
            # Cloud uses cursor-based pagination
            cursor = None

            while True:
                try:
                    page_count += 1
                    logger.debug(
                        f"Fetching page {page_count} of Confluence content (cursor={cursor})"
                    )
                    response = await self._get_space_content_cloud(cursor)
                    results = response.get("results", [])

                    if not results:
                        logger.debug("No more results found, ending pagination")
                        break

                    total_documents += len(results)
                    logger.debug(
                        f"Processing {len(results)} documents from page {page_count}"
                    )

                    # Process each content item
                    for content in results:
                        if self._should_process_content(content):
                            try:
                                document = self._process_content(
                                    content, clean_html=True
                                )
                                if document:
                                    documents.append(document)

                                    # Process attachments if enabled
                                    if (
                                        self.config.download_attachments
                                        and self.attachment_downloader
                                    ):
                                        try:
                                            content_id = content.get("id")
                                            attachments = (
                                                await self._get_content_attachments(
                                                    content_id
                                                )
                                            )

                                            if attachments:
                                                attachment_docs = await self.attachment_downloader.download_and_process_attachments(
                                                    attachments, document
                                                )
                                                documents.extend(attachment_docs)

                                                logger.debug(
                                                    f"Processed {len(attachment_docs)} attachments for {content['type']} '{content['title']}'"
                                                )
                                        except Exception as e:
                                            logger.error(
                                                f"Failed to process attachments for {content['type']} '{content['title']}' "
                                                f"(ID: {content['id']}): {e!s}"
                                            )

                                    logger.debug(
                                        f"Processed {content['type']} '{content['title']}' "
                                        f"(ID: {content['id']}) from space {self.config.space_key}"
                                    )
                            except Exception as e:
                                logger.error(
                                    f"Failed to process {content['type']} '{content['title']}' "
                                    f"(ID: {content['id']}): {e!s}"
                                )

                    # Get the next cursor from the response
                    next_url = response.get("_links", {}).get("next")
                    if not next_url:
                        logger.debug("No next page link found, ending pagination")
                        break

                    # Extract just the cursor value from the URL
                    try:
                        from urllib.parse import parse_qs, urlparse

                        parsed_url = urlparse(next_url)
                        query_params = parse_qs(parsed_url.query)
                        cursor = query_params.get("cursor", [None])[0]
                        if not cursor:
                            logger.debug(
                                "No cursor found in next URL, ending pagination"
                            )
                            break
                        logger.debug(f"Found next cursor: {cursor}")
                    except Exception as e:
                        logger.error(f"Failed to parse next URL: {e!s}")
                        break

                except Exception as e:
                    logger.error(
                        f"Failed to fetch content from space {self.config.space_key}: {e!s}"
                    )
                    raise
        else:
            # Data Center/Server uses start/limit pagination
            start = 0
            limit = 25

            while True:
                try:
                    page_count += 1
                    logger.debug(
                        f"Fetching page {page_count} of Confluence content (start={start})"
                    )
                    response = await self._get_space_content_datacenter(start)
                    results = response.get("results", [])

                    if not results:
                        logger.debug("No more results found, ending pagination")
                        break

                    total_documents += len(results)
                    logger.debug(
                        f"Processing {len(results)} documents from page {page_count}"
                    )

                    # Process each content item
                    for content in results:
                        if self._should_process_content(content):
                            try:
                                document = self._process_content(
                                    content, clean_html=True
                                )
                                if document:
                                    documents.append(document)

                                    # Process attachments if enabled
                                    if (
                                        self.config.download_attachments
                                        and self.attachment_downloader
                                    ):
                                        try:
                                            content_id = content.get("id")
                                            attachments = (
                                                await self._get_content_attachments(
                                                    content_id
                                                )
                                            )

                                            if attachments:
                                                attachment_docs = await self.attachment_downloader.download_and_process_attachments(
                                                    attachments, document
                                                )
                                                documents.extend(attachment_docs)

                                                logger.debug(
                                                    f"Processed {len(attachment_docs)} attachments for {content['type']} '{content['title']}'"
                                                )
                                        except Exception as e:
                                            logger.error(
                                                f"Failed to process attachments for {content['type']} '{content['title']}' "
                                                f"(ID: {content['id']}): {e!s}"
                                            )

                                    logger.debug(
                                        f"Processed {content['type']} '{content['title']}' "
                                        f"(ID: {content['id']}) from space {self.config.space_key}"
                                    )
                            except Exception as e:
                                logger.error(
                                    f"Failed to process {content['type']} '{content['title']}' "
                                    f"(ID: {content['id']}): {e!s}"
                                )

                    # Check if there are more pages
                    total_size = response.get("totalSize", response.get("size", 0))
                    if start + limit >= total_size:
                        logger.debug(
                            f"Reached end of results: {start + limit} >= {total_size}"
                        )
                        break

                    # Move to next page
                    start += limit
                    logger.debug(f"Moving to next page with start={start}")

                except Exception as e:
                    logger.error(
                        f"Failed to fetch content from space {self.config.space_key}: {e!s}"
                    )
                    raise

        logger.info(
            f"📄 Confluence: {len(documents)} documents from space {self.config.space_key}"
        )
        return documents
