from typing import List, Optional, Dict, Any
import os
import requests
from requests.auth import HTTPBasicAuth
from qdrant_loader.config import ConfluenceConfig
from qdrant_loader.core.document import Document
from qdrant_loader.utils.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)

class ConfluenceConnector:
    """Connector for Atlassian Confluence."""
    
    def __init__(self, config: ConfluenceConfig):
        """Initialize the connector with configuration.
        
        Args:
            config: Confluence configuration
        """
        self.config = config
        self.base_url = config.url.rstrip("/")
        
        # Get authentication token
        self.token = os.getenv("CONFLUENCE_TOKEN")
        if not self.token:
            raise ValueError("CONFLUENCE_TOKEN environment variable is not set")
            
        # Initialize session with authentication
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth("", self.token)
        
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
            "spaceKey": self.config.space_key,
            "expand": "body.storage,version,metadata.labels",
            "start": start,
            "limit": limit,
            "type": ",".join(self.config.content_types)
        }
        return self._make_request("GET", "content", params=params)

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

    def _process_content(self, content: Dict[str, Any]) -> Document:
        """Process a single piece of Confluence content into a Document.
        
        Args:
            content: Content data from Confluence API
            
        Returns:
            Document: Processed document
        """
        # Extract metadata
        metadata = {
            "id": content["id"],
            "type": content["type"],
            "title": content["title"],
            "space_key": self.config.space_key,
            "version": content["version"]["number"],
            "last_modified": content["version"]["when"],
            "url": f"{self.base_url}/spaces/{self.config.space_key}/pages/{content['id']}",
            "labels": [
                label["name"]
                for label in content.get("metadata", {}).get("labels", {}).get("results", [])
            ]
        }
        
        # Extract content
        body = content["body"]["storage"]["value"]
        
        return Document(
            content=body,
            metadata=metadata,
            source=f"confluence/{self.config.space_key}",
            source_type="confluence",
            url=metadata["url"],
            last_updated=datetime.fromisoformat(metadata["last_modified"])
        )
            
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
                            document = self._process_content(content)
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
                
                # Check if there are more results
                if len(results) < limit:
                    break
                    
                start += limit
                
            except Exception as e:
                logger.error(f"Failed to fetch content from space {self.config.space_key}: {str(e)}")
                raise
                
        logger.info(f"Processed {len(documents)} documents from space {self.config.space_key}")
        return documents 