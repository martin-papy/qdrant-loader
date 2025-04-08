from typing import List, Optional, Dict, Any
import os
import requests
from requests.auth import HTTPBasicAuth
from .config import ConfluenceSpaceConfig
from qdrant_loader.core.document import Document
from qdrant_loader.utils.logger import get_logger
from datetime import datetime
import re

logger = get_logger(__name__)

class ConfluenceConnector:
    """Connector for Atlassian Confluence."""
    
    def __init__(self, config: ConfluenceSpaceConfig):
        """Initialize the connector with configuration.
        
        Args:
            config: Confluence configuration
        """
        self.config = config
        self.base_url = config.url.rstrip("/")
        
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
        
    def _get_api_url(self, endpoint: str) -> str:
        """Construct the full API URL for an endpoint.
        
        Args:
            endpoint: API endpoint path
            
        Returns:
            str: Full API URL
        """
        return f"{self.base_url}/rest/api/{endpoint}"
        
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an authenticated request to the Confluence API.
        
        Args:
            method: HTTP method
            endpoint: API endpoint path
            **kwargs: Additional request parameters
            
        Returns:
            Dict[str, Any]: Response data
            
        Raises:
            requests.exceptions.RequestException: If the request fails
        """
        url = self._get_api_url(endpoint)
        try:
            kwargs["auth"] = self.session.auth
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to make request to {url}: {str(e)}")
            raise

    def _get_space_content(self, start: int = 0, limit: int = 25) -> Dict[str, Any]:
        """Fetch content from a Confluence space.
        
        Args:
            start: Starting index for pagination
            limit: Maximum number of items to return
            
        Returns:
            Dict[str, Any]: Response containing space content
        """
        params = {
            "cql": f"space = {self.config.space_key} and type in (page, blogpost)",
            "expand": "body.storage,version,metadata.labels,history,space,extensions.position",
            "start": start,
            "limit": limit
        }
        logger.debug("Making Confluence API request", url=f"{self.base_url}/rest/api/content/search", params=params)
        response = self._make_request("GET", "content/search", params=params)
        if response and "results" in response:
            logger.info(f"Found {len(response['results'])} documents in Confluence space", 
                       count=len(response["results"]), 
                       total_size=response.get("size", 0))
        logger.debug("Confluence API response", response=response)
        return response

    def _should_process_content(self, content: Dict[str, Any]) -> bool:
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
        
        # Check exclude labels first
        if any(label in labels for label in self.config.exclude_labels):
            return False
            
        # If include labels are specified, content must have at least one
        if self.config.include_labels:
            return any(label in labels for label in self.config.include_labels)
            
        return True

    def _process_content(self, content: Dict[str, Any], clean_html: bool = True) -> Optional[Document]:
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
            content_id = content.get('id')
            title = content.get('title')
            body = content.get('body', {}).get('storage', {}).get('value')
            space = content.get('space', {}).get('key')
            
            # Check for missing or malformed body
            if not body:
                raise ValueError("Content body is missing or malformed")
            
            # Check for other missing required fields
            missing_fields = []
            if not content_id:
                missing_fields.append('id')
            if not title:
                missing_fields.append('title')
            if not space:
                missing_fields.append('space')
            
            if missing_fields:
                raise ValueError(f"Content is missing required fields: {', '.join(missing_fields)}")

            # Get version information
            version = content.get('version', {})
            version_number = version.get('number', 1) if isinstance(version, dict) else 1

            # Get URL and author information
            url = content.get('_links', {}).get('webui', '')
            author = content.get('history', {}).get('createdBy', {}).get('displayName')
            last_updated = None
            if 'version' in content and 'when' in content['version']:
                try:
                    last_updated = content['version']['when']
                except (ValueError, TypeError):
                    pass

            # Create metadata
            metadata = {
                'id': content_id,
                'title': title,
                'space': space,
                'version': version_number,
                'type': content.get('type', 'unknown'),
                'labels': [
                    label['name']
                    for label in content.get('metadata', {}).get('labels', {}).get('results', [])
                ],
                'last_modified': last_updated
            }

            # Clean content if requested
            content_text = self._clean_html(body) if clean_html else body

            # Create document with all fields
            return Document(
                id=content_id,
                content=content_text,
                source=f"{self.base_url}/spaces/{space}/pages/{content_id}",
                source_type="confluence",
                metadata=metadata,
                url=url,
                author=author,
                last_updated=last_updated,
                project=space
            )
        except Exception as e:
            logger.error(f"Failed to process content: {str(e)}")
            raise

    def _clean_html(self, html: str) -> str:
        """Clean HTML content by removing tags and special characters.
        
        Args:
            html: HTML content to clean
            
        Returns:
            Cleaned text
        """
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', html)
        # Replace special characters
        text = re.sub(r'&[^;]+;', ' ', text)
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def get_documents(self) -> List[Document]:
        """Fetch and process documents from Confluence.
        
        Returns:
            List[Document]: List of processed documents
        """
        documents = []
        start = 0
        limit = 25
        
        while True:
            try:
                response = self._get_space_content(start, limit)
                results = response.get("results", [])
                
                if not results:
                    break
                    
                # Process each content item
                for content in results:
                    if self._should_process_content(content):
                        try:
                            document = self._process_content(content, clean_html=False)
                            if document:
                                documents.append(document)
                                logger.info(
                                    f"Processed {content['type']} '{content['title']}' "
                                    f"(ID: {content['id']}) from space {self.config.space_key}"
                                )
                        except Exception as e:
                            logger.error(
                                f"Failed to process {content['type']} '{content['title']}' "
                                f"(ID: {content['id']}): {str(e)}"
                            )
                
                # Check if there are more results using the size and start parameters
                total_size = response.get("size", 0)
                if start + limit >= total_size:
                    break
                start += limit
                
            except Exception as e:
                logger.error(f"Failed to fetch content from space {self.config.space_key}: {str(e)}")
                raise
                
        logger.info(f"Processed {len(documents)} documents from space {self.config.space_key}")
        return documents 