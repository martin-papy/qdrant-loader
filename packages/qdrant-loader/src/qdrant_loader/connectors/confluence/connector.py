import re
from datetime import datetime
from urllib.parse import quote, urljoin

import requests

from qdrant_loader.config.types import SourceType
from qdrant_loader.connectors.base import BaseConnector
from qdrant_loader.connectors.confluence.auth import (
    auto_detect_deployment_type as _auto_detect_type,
)
from qdrant_loader.connectors.confluence.auth import setup_authentication as _setup_auth
from qdrant_loader.connectors.confluence.config import (
    ConfluenceDeploymentType,
    ConfluenceSpaceConfig,
)
from qdrant_loader.connectors.confluence.mappers import (
    extract_hierarchy_info as _extract_hierarchy_info_helper,
)
from qdrant_loader.connectors.confluence.pagination import (
    build_cloud_search_params as _build_cloud_params,
)
from qdrant_loader.connectors.confluence.pagination import (
    build_dc_search_params as _build_dc_params,
)
from qdrant_loader.connectors.shared.attachments import AttachmentReader
from qdrant_loader.connectors.shared.attachments.metadata import (
    confluence_attachment_to_metadata,
)
from qdrant_loader.connectors.shared.http import (
    RateLimiter,
)
from qdrant_loader.connectors.shared.http import (
    request_with_policy as _http_request_with_policy,
)
from qdrant_loader.core.attachment_downloader import AttachmentMetadata
from qdrant_loader.core.document import Document
from qdrant_loader.core.file_conversion import (
    FileConversionConfig,
    FileConverter,
    FileDetector,
)
from qdrant_loader.utils.logging import LoggingConfig

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
        # Rate limiter (configurable RPM)
        self._rate_limiter = RateLimiter.per_minute(
            getattr(self.config, "requests_per_minute", 60)
        )

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
                from qdrant_loader.core.attachment_downloader import (
                    AttachmentDownloader,
                )

                downloader = AttachmentDownloader(
                    session=self.session,
                    file_conversion_config=file_conversion_config,
                    enable_file_conversion=True,
                    max_attachment_size=file_conversion_config.max_file_size,
                )
                self.attachment_downloader = AttachmentReader(
                    session=self.session, downloader=downloader
                )
                logger.info("Attachment reader initialized with file conversion")
            else:
                logger.debug("Attachment downloading disabled")

            logger.debug("File converter initialized with global config")

    def _setup_authentication(self):
        """Set up authentication based on deployment type."""
        _setup_auth(self.session, self.config)

    def _auto_detect_deployment_type(self) -> ConfluenceDeploymentType:
        """Auto-detect the Confluence deployment type based on the base URL.

        Returns:
            ConfluenceDeploymentType: Detected deployment type
        """
        return _auto_detect_type(str(self.base_url))

    async def __aenter__(self):
        """Async context manager entry."""
        if not self._initialized:
            self._initialized = True
        return self

    async def __aexit__(self, exc_type, exc_val, _exc_tb):
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
            if not self.session.headers.get("Authorization"):
                kwargs["auth"] = self.session.auth

            response = await _http_request_with_policy(
                self.session,
                method,
                url,
                rate_limiter=self._rate_limiter,
                retries=3,
                backoff_factor=0.5,
                status_forcelist=(429, 500, 502, 503, 504),
                overall_timeout=90.0,
                **kwargs,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to make request to {url}: {e}")
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
        # Build params via helper
        params = _build_cloud_params(
            self.config.space_key, self.config.content_types, cursor
        )

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
        params = _build_dc_params(
            self.config.space_key, self.config.content_types, start
        )

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
                    translated = confluence_attachment_to_metadata(
                        attachment_data,
                        base_url=str(self.base_url),
                        parent_id=content_id,
                    )
                    if translated is None:
                        logger.warning(
                            "No download link found for attachment",
                            attachment_id=attachment_data.get("id"),
                            filename=attachment_data.get("title"),
                            deployment_type=self.config.deployment_type,
                        )
                        continue

                    attachments.append(translated)

                    logger.debug(
                        "Found attachment",
                        attachment_id=getattr(translated, "id", None),
                        filename=getattr(translated, "filename", None),
                        size=getattr(translated, "size", None),
                        mime_type=getattr(translated, "mime_type", None),
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

    async def _process_attachments_for_document(
        self, content: dict, document: Document
    ) -> list[Document]:
        """Process attachments for a given content item and parent document.

        Checks configuration flags and uses the attachment downloader to
        fetch and convert attachments into child documents.

        Args:
            content: Confluence content item
            document: Parent document corresponding to the content item

        Returns:
            List of generated attachment documents (may be empty)
        """
        if not (self.config.download_attachments and self.attachment_downloader):
            return []

        try:
            content_id = content.get("id")
            attachments = await self._get_content_attachments(content_id)
            if not attachments:
                return []

            attachment_docs = await self.attachment_downloader.fetch_and_process(
                attachments, document
            )
            logger.debug(
                f"Processed {len(attachment_docs)} attachments for {content.get('type')} '{content.get('title')}'",
                content_id=content.get("id"),
            )
            return attachment_docs
        except Exception as e:
            logger.error(
                f"Failed to process attachments for {content.get('type')} '{content.get('title')}' (ID: {content.get('id')}): {e!s}"
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
        return _extract_hierarchy_info_helper(content)

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

            # Build canonical and display URLs
            canonical_url = self._construct_canonical_page_url(
                space or "",
                content_id or "",
                content.get("type", "page"),
            )
            display_url = self._construct_page_url(
                space or "",
                content_id or "",
                title or "",
                content.get("type", "page"),
            )

            # Create metadata with all available information including hierarchy
            metadata = {
                "id": content_id,
                "title": title,
                "space": space,
                "version": version_number,
                "type": content.get("type", "unknown"),
                "author": author,
                # Human-friendly URL (kept in metadata)
                "display_url": display_url,
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
                url=canonical_url,
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
        self, space: str, content_id: str, title: str, content_type: str = "page"
    ) -> str:
        """Construct the appropriate URL for a Confluence page based on deployment type.

        Args:
            space: The space key
            content_id: The content ID
            title: The page title (used for Data Center URLs)
            content_type: The type of content (page, blogpost, etc.)

        Returns:
            The constructed URL
        """
        # Ensure base is treated as a directory to preserve any path components
        base = str(self.base_url)
        base = base if base.endswith("/") else base + "/"

        if self.config.deployment_type == ConfluenceDeploymentType.CLOUD:
            # Cloud URLs use ID-based format
            if content_type == "blogpost":
                path = f"spaces/{space}/blog/{content_id}"
            else:
                path = f"spaces/{space}/pages/{content_id}"
            return urljoin(base, path)
        else:
            # Data Center/Server URLs - use title for better readability
            # URL-encode the title, replacing spaces with '+' (Confluence format)
            encoded_title = quote(title.replace(" ", "+"), safe="+")
            if content_type == "blogpost":
                path = f"display/{space}/{encoded_title}"
            else:
                path = f"display/{space}/{encoded_title}"
            return urljoin(base, path)

    def _construct_canonical_page_url(
        self, space: str, content_id: str, content_type: str = "page"
    ) -> str:
        """Construct a canonical ID-based URL for both Cloud and Data Center."""
        base = str(self.base_url)
        base = base if base.endswith("/") else base + "/"

        if content_type == "blogpost":
            path = f"spaces/{space}/blog/{content_id}"
        else:
            path = f"spaces/{space}/pages/{content_id}"
        return urljoin(base, path)

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

                                    attachment_docs = (
                                        await self._process_attachments_for_document(
                                            content, document
                                        )
                                    )
                                    documents.extend(attachment_docs)

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

                                    attachment_docs = (
                                        await self._process_attachments_for_document(
                                            content, document
                                        )
                                    )
                                    documents.extend(attachment_docs)

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
