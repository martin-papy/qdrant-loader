import asyncio
import os
import re

import requests
from requests.auth import HTTPBasicAuth

from qdrant_loader.config.types import SourceType
from qdrant_loader.connectors.base import BaseConnector
from qdrant_loader.connectors.confluence.config import ConfluenceSpaceConfig
from qdrant_loader.core.document import Document
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

        # Get authentication token and email
        self.token = os.getenv("CONFLUENCE_TOKEN")
        self.email = os.getenv("CONFLUENCE_EMAIL")
        if not self.token:
            raise ValueError("CONFLUENCE_TOKEN environment variable is not set")
        if not self.email:
            raise ValueError("CONFLUENCE_EMAIL environment variable is not set")

        # Initialize session with authentication
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(self.email, self.token)
        self._initialized = False

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
            kwargs["auth"] = self.session.auth
            response = await asyncio.to_thread(self.session.request, method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to make request to {url}: {e}")
            raise

    async def _get_space_content(self, cursor: str | None = None) -> dict:
        """Fetch content from a Confluence space.

        Args:
            cursor: Cursor for pagination. If None, starts from the beginning.

        Returns:
            dict: Response containing space content
        """
        if not self.config.content_types:
            params = {
                "cql": f"space = {self.config.space_key}",
                "expand": "body.storage,version,metadata.labels,history,space,extensions.position,children.comment.body.storage",
                "limit": 25,  # Using a reasonable default limit
            }
        else:
            params = {
                "cql": f"space = {self.config.space_key} and type in ({','.join(self.config.content_types)})",
                "expand": "body.storage,version,metadata.labels,history,space,extensions.position,children.comment.body.storage",
                "limit": 25,  # Using a reasonable default limit
            }

        # Add cursor if provided
        if cursor:
            params["cursor"] = cursor

        logger.debug(
            "Making Confluence API request",
            url=f"{self.base_url}/rest/api/content/search",
            params=params,
        )
        response = await self._make_request("GET", "content/search", params=params)
        if response and "results" in response:
            logger.info(
                f"Found {len(response['results'])} documents in Confluence space",
                count=len(response["results"]),
                total_size=response.get("size", 0),
            )
        logger.debug("Confluence API response", response=response)
        return response

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
            for label in content.get("metadata", {}).get("labels", {}).get("results", [])
        }

        # Check exclude labels first, if there are any specified
        if self.config.exclude_labels and any(
            label in labels for label in self.config.exclude_labels
        ):
            return False

        # If include labels are specified, content must have at least one
        if self.config.include_labels:
            return any(label in labels for label in self.config.include_labels)

        return True

    def _process_content(self, content: dict, clean_html: bool = True) -> Document | None:
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
            logger.debug(f"Processing content: {title} - ({content_id}) in space {space}")

            body = content.get("body", {}).get("storage", {}).get("value")
            # Check for missing or malformed body
            if not body:
                raise ValueError("Content body is missing or malformed")

            # Check for other missing required fields
            missing_fields = []
            if not content_id:
                missing_fields.append("id")
            if not title:
                missing_fields.append("title")
            if not space:
                missing_fields.append("space")

            if missing_fields:
                raise ValueError(f"Content is missing required fields: {', '.join(missing_fields)}")

            # Get version information
            version = content.get("version", {})
            version_number = version.get("number", 1) if isinstance(version, dict) else 1

            # Get URL and author information
            author = content.get("history", {}).get("createdBy", {}).get("displayName")
            created_at = None
            if "history" in content and "createdDate" in content["history"]:
                try:
                    created_at = content["history"]["createdDate"]
                except (ValueError, TypeError):
                    pass
            updated_at = None
            if "version" in content and "when" in content["version"]:
                try:
                    updated_at = content["version"]["when"]
                except (ValueError, TypeError):
                    pass

            # Process comments
            comments = []
            if "children" in content and "comment" in content["children"]:
                for comment in content["children"]["comment"]["results"]:
                    comment_body = comment.get("body", {}).get("storage", {}).get("value", "")
                    comment_author = (
                        comment.get("history", {}).get("createdBy", {}).get("displayName", "")
                    )
                    comment_created = comment.get("history", {}).get("createdDate", "")
                    comments.append(
                        {
                            "body": self._clean_html(comment_body) if clean_html else comment_body,
                            "author": comment_author,
                            "created_at": comment_created,
                        }
                    )

            # Create metadata
            metadata = {
                "id": content_id,
                "title": title,
                "space": space,
                "version": version_number,
                "type": content.get("type", "unknown"),
                "author": author,
                "labels": [
                    label["name"]
                    for label in content.get("metadata", {}).get("labels", {}).get("results", [])
                ],
                "comments": comments,
                "updated_at": updated_at,
                "created_at": created_at,
            }

            # Clean content if requested
            content_text = self._clean_html(body) if clean_html else body

            # Create document with all fields
            document = Document(
                title=title,
                content=content_text,
                metadata=metadata,
                source_type=SourceType.CONFLUENCE,
                source=self.config.source,
                url=f"{self.base_url}/spaces/{space}/pages/{content_id}",
                is_deleted=False,
                updated_at=updated_at,
                created_at=created_at,
            )

            return document

        except Exception as e:
            logger.error(
                "Failed to process content",
                content_id=content.get("id"),
                content_title=content.get("title"),
                content_type=content.get("type"),
                error=str(e),
            )
            raise

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
        cursor = None

        while True:
            try:
                response = await self._get_space_content(cursor)
                results = response.get("results", [])

                if not results:
                    break

                # Process each content item
                for content in results:
                    if self._should_process_content(content):
                        try:
                            document = self._process_content(content, clean_html=True)
                            if document:
                                documents.append(document)
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
                    break

                # Extract just the cursor value from the URL
                try:
                    from urllib.parse import parse_qs, urlparse

                    parsed_url = urlparse(next_url)
                    query_params = parse_qs(parsed_url.query)
                    cursor = query_params.get("cursor", [None])[0]
                    if not cursor:
                        break
                except Exception as e:
                    logger.error(f"Failed to parse next URL: {e!s}")
                    break

            except Exception as e:
                logger.error(f"Failed to fetch content from space {self.config.space_key}: {e!s}")
                raise

        logger.info(f"Processed {len(documents)} documents from space {self.config.space_key}")
        return documents
