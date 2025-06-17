# SharePoint Connector Implementation Guide

**Document Version:** 1.0  
**Date:** January 2025  
**Status:** Implementation Specification

## 1. Core Implementation Structure

### 1.1 Connector Class Implementation

```python
# packages/qdrant-loader/src/qdrant_loader/connectors/sharepoint/connector.py

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin

from qdrant_loader.config.types import SourceType
from qdrant_loader.connectors.base import BaseConnector
from qdrant_loader.connectors.sharepoint.config import SharePointConfig
from qdrant_loader.connectors.sharepoint.client import SharePointClient
from qdrant_loader.connectors.sharepoint.auth import SharePointAuthenticator
from qdrant_loader.connectors.sharepoint.processors import (
    SiteProcessor,
    DocumentProcessor,
    PageProcessor,
    ListProcessor
)
from qdrant_loader.core.document import Document
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class SharePointConnector(BaseConnector):
    """SharePoint connector for both Online and Server deployments."""

    def __init__(self, config: SharePointConfig):
        """Initialize SharePoint connector.
        
        Args:
            config: SharePoint configuration object
        """
        super().__init__(config)
        self.config = config
        
        # Initialize components
        self.authenticator = SharePointAuthenticator(config)
        self.client = SharePointClient(config, self.authenticator)
        
        # Initialize processors
        self.site_processor = SiteProcessor(self.client, config)
        self.document_processor = DocumentProcessor(self.client, config)
        self.page_processor = PageProcessor(self.client, config)
        self.list_processor = ListProcessor(self.client, config)
        
        # State tracking
        self._sites_cache: Dict[str, Any] = {}
        self._processed_items: int = 0

    async def __aenter__(self):
        """Async context manager entry."""
        await super().__aenter__()
        await self.authenticator.initialize()
        await self.client.initialize()
        logger.info("SharePoint connector initialized", 
                   base_url=self.config.base_url,
                   auth_method=self.config.auth_method)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.close()
        await super().__aexit__(exc_type, exc_val, exc_tb)
        logger.info("SharePoint connector closed")

    async def get_documents(self) -> List[Document]:
        """Get documents from SharePoint sources.
        
        Returns:
            List of Document objects
        """
        logger.info("Starting SharePoint document collection")
        documents = []
        
        try:
            # Discover sites based on configuration
            sites = await self._discover_sites()
            logger.info(f"Discovered {len(sites)} SharePoint sites")
            
            # Process each site
            for site in sites:
                site_documents = await self._process_site(site)
                documents.extend(site_documents)
                self._processed_items += len(site_documents)
                
                if self._processed_items % 100 == 0:
                    logger.info(f"Processed {self._processed_items} items so far")
            
            logger.info(f"SharePoint collection complete: {len(documents)} documents")
            return documents
            
        except Exception as e:
            logger.error(f"Error during SharePoint collection: {e}")
            raise

    async def _discover_sites(self) -> List[Dict[str, Any]]:
        """Discover SharePoint sites based on configuration."""
        if self.config.discovery_scope == "specific_sites":
            return await self._get_specific_sites()
        elif self.config.discovery_scope == "site_collection":
            return await self._get_site_collection_sites()
        else:
            return await self._get_tenant_sites()

    async def _process_site(self, site: Dict[str, Any]) -> List[Document]:
        """Process a single SharePoint site."""
        site_url = site.get("url", "")
        site_title = site.get("title", "Unknown Site")
        
        logger.debug(f"Processing site: {site_title}")
        documents = []
        
        try:
            # Process document libraries
            if self.config.include_document_libraries:
                library_docs = await self.document_processor.process_site_libraries(site)
                documents.extend(library_docs)
            
            # Process pages
            if self.config.include_pages:
                page_docs = await self.page_processor.process_site_pages(site)
                documents.extend(page_docs)
            
            # Process lists
            if self.config.include_lists:
                list_docs = await self.list_processor.process_site_lists(site)
                documents.extend(list_docs)
            
            return documents
            
        except Exception as e:
            logger.error(f"Error processing site {site_title}: {e}")
            return []
```

### 1.2 Configuration Schema

```python
# packages/qdrant-loader/src/qdrant_loader/connectors/sharepoint/config.py

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from qdrant_loader.config.source_config import SourceConfig


class AuthMethod(str, Enum):
    """SharePoint authentication methods."""
    OAUTH = "oauth"
    SERVICE_PRINCIPAL = "service_principal"
    CERTIFICATE = "certificate"
    NTLM = "ntlm"


class DiscoveryScope(str, Enum):
    """SharePoint discovery scope options."""
    TENANT = "tenant"
    SITE_COLLECTION = "site_collection"
    SPECIFIC_SITES = "specific_sites"


class SharePointConfig(SourceConfig):
    """Configuration for SharePoint connector."""
    
    # Authentication
    auth_method: AuthMethod = Field(default=AuthMethod.OAUTH)
    tenant_id: Optional[str] = Field(default=None)
    client_id: Optional[str] = Field(default=None)
    client_secret: Optional[str] = Field(default=None)
    certificate_path: Optional[str] = Field(default=None)
    certificate_password: Optional[str] = Field(default=None)
    username: Optional[str] = Field(default=None)  # For NTLM
    password: Optional[str] = Field(default=None)  # For NTLM
    
    # Discovery configuration
    discovery_scope: DiscoveryScope = Field(default=DiscoveryScope.TENANT)
    site_collections: List[str] = Field(default_factory=list)
    specific_sites: List[str] = Field(default_factory=list)
    include_subsites: bool = Field(default=True)
    max_sites: int = Field(default=1000)
    
    # Content processing
    include_document_libraries: bool = Field(default=True)
    include_lists: bool = Field(default=True)
    include_pages: bool = Field(default=True)
    include_attachments: bool = Field(default=True)
    max_file_size_mb: int = Field(default=100)
    supported_file_types: List[str] = Field(
        default_factory=lambda: ["docx", "xlsx", "pptx", "pdf", "txt", "md"]
    )
    
    # Performance and reliability
    max_concurrent_requests: int = Field(default=5)
    rate_limit_rpm: int = Field(default=600)
    rate_limit_rph: int = Field(default=10000)
    request_timeout: int = Field(default=30)
    max_retries: int = Field(default=3)
    
    # Advanced features
    enable_incremental_sync: bool = Field(default=True)
    enable_analytics: bool = Field(default=False)
    enable_taxonomy_extraction: bool = Field(default=True)
    enable_permission_tracking: bool = Field(default=False)
    
    @validator('auth_method')
    def validate_auth_config(cls, v, values):
        """Validate authentication configuration completeness."""
        if v == AuthMethod.OAUTH and not values.get('client_id'):
            raise ValueError("client_id required for OAuth authentication")
        if v == AuthMethod.SERVICE_PRINCIPAL and not all([
            values.get('tenant_id'), 
            values.get('client_id'), 
            values.get('client_secret')
        ]):
            raise ValueError("tenant_id, client_id, and client_secret required for service principal")
        return v
    
    class Config:
        env_prefix = "SHAREPOINT_"
        case_sensitive = False
```

### 1.3 Authentication Implementation

```python
# packages/qdrant-loader/src/qdrant_loader/connectors/sharepoint/auth.py

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import msal
import httpx
from qdrant_loader.connectors.sharepoint.config import SharePointConfig, AuthMethod
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class SharePointAuthenticator:
    """Handles SharePoint authentication across different methods."""
    
    def __init__(self, config: SharePointConfig):
        self.config = config
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        self.msal_app: Optional[msal.ConfidentialClientApplication] = None
        
    async def initialize(self):
        """Initialize authentication components."""
        if self.config.auth_method in [AuthMethod.OAUTH, AuthMethod.SERVICE_PRINCIPAL]:
            self._initialize_msal()
        
    def _initialize_msal(self):
        """Initialize MSAL application for OAuth/Service Principal auth."""
        if self.config.auth_method == AuthMethod.SERVICE_PRINCIPAL:
            # Service Principal with client secret
            self.msal_app = msal.ConfidentialClientApplication(
                client_id=self.config.client_id,
                client_credential=self.config.client_secret,
                authority=f"https://login.microsoftonline.com/{self.config.tenant_id}"
            )
        elif self.config.auth_method == AuthMethod.CERTIFICATE:
            # Certificate-based authentication
            self.msal_app = msal.ConfidentialClientApplication(
                client_id=self.config.client_id,
                client_credential={
                    "private_key": self._load_private_key(),
                    "thumbprint": self._get_certificate_thumbprint()
                },
                authority=f"https://login.microsoftonline.com/{self.config.tenant_id}"
            )
    
    async def get_access_token(self) -> str:
        """Get valid access token, refreshing if necessary."""
        if self._token_is_valid():
            return self.access_token
            
        return await self._acquire_new_token()
    
    def _token_is_valid(self) -> bool:
        """Check if current token is valid."""
        if not self.access_token or not self.token_expires_at:
            return False
        
        # Add 5-minute buffer to prevent edge cases
        buffer_time = datetime.now() + timedelta(minutes=5)
        return self.token_expires_at > buffer_time
    
    async def _acquire_new_token(self) -> str:
        """Acquire new access token based on auth method."""
        if self.config.auth_method == AuthMethod.SERVICE_PRINCIPAL:
            return await self._acquire_service_principal_token()
        elif self.config.auth_method == AuthMethod.CERTIFICATE:
            return await self._acquire_certificate_token()
        elif self.config.auth_method == AuthMethod.OAUTH:
            return await self._acquire_oauth_token()
        elif self.config.auth_method == AuthMethod.NTLM:
            return await self._acquire_ntlm_token()
        else:
            raise ValueError(f"Unsupported auth method: {self.config.auth_method}")
    
    async def _acquire_service_principal_token(self) -> str:
        """Acquire token using service principal credentials."""
        scopes = ["https://graph.microsoft.com/.default"]
        
        # Run MSAL in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, 
            lambda: self.msal_app.acquire_token_for_client(scopes=scopes)
        )
        
        if "access_token" in result:
            self.access_token = result["access_token"]
            # MSAL returns expires_in in seconds
            expires_in = result.get("expires_in", 3600)
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            logger.info("Successfully acquired service principal token")
            return self.access_token
        else:
            error_msg = result.get("error_description", "Unknown error")
            logger.error(f"Failed to acquire service principal token: {error_msg}")
            raise Exception(f"Authentication failed: {error_msg}")
```

### 1.4 SharePoint Client Implementation

```python
# packages/qdrant-loader/src/qdrant_loader/connectors/sharepoint/client.py

import asyncio
from typing import Dict, Any, List, Optional
import httpx
from urllib.parse import urljoin
from qdrant_loader.connectors.sharepoint.config import SharePointConfig
from qdrant_loader.connectors.sharepoint.auth import SharePointAuthenticator
from qdrant_loader.connectors.sharepoint.rate_limiter import RateLimiter
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class SharePointClient:
    """HTTP client for SharePoint REST API operations."""
    
    def __init__(self, config: SharePointConfig, authenticator: SharePointAuthenticator):
        self.config = config
        self.authenticator = authenticator
        self.base_url = str(config.base_url)
        self.client: Optional[httpx.AsyncClient] = None
        self.rate_limiter = RateLimiter(
            requests_per_minute=config.rate_limit_rpm,
            requests_per_hour=config.rate_limit_rph
        )
        
    async def initialize(self):
        """Initialize HTTP client."""
        timeout = httpx.Timeout(self.config.request_timeout)
        self.client = httpx.AsyncClient(
            timeout=timeout,
            limits=httpx.Limits(max_connections=self.config.max_concurrent_requests)
        )
        
    async def close(self):
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
    
    async def get(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Perform GET request to SharePoint API."""
        return await self._request("GET", endpoint, params=params)
    
    async def post(self, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Perform POST request to SharePoint API."""
        return await self._request("POST", endpoint, json=data)
    
    async def _request(
        self, 
        method: str, 
        endpoint: str, 
        params: Dict[str, Any] = None,
        json: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Perform HTTP request with authentication and error handling."""
        url = self._build_url(endpoint)
        
        for attempt in range(self.config.max_retries):
            try:
                # Rate limiting
                await self.rate_limiter.acquire()
                
                # Get fresh access token
                access_token = await self.authenticator.get_access_token()
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                }
                
                # Make request
                response = await self.client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=json
                )
                
                # Handle response
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    # Rate limited - wait and retry
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(f"Rate limited, waiting {retry_after} seconds")
                    await asyncio.sleep(retry_after)
                    continue
                elif response.status_code == 401:
                    # Authentication error - refresh token and retry
                    logger.warning("Authentication error, refreshing token")
                    self.authenticator.access_token = None
                    continue
                else:
                    response.raise_for_status()
                    
            except httpx.TimeoutException:
                if attempt == self.config.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
            except Exception as e:
                if attempt == self.config.max_retries - 1:
                    raise
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                await asyncio.sleep(2 ** attempt)
        
        raise Exception(f"Request failed after {self.config.max_retries} attempts")
    
    def _build_url(self, endpoint: str) -> str:
        """Build complete URL for API endpoint."""
        if endpoint.startswith("http"):
            return endpoint
        
        # Ensure proper API path structure
        if not endpoint.startswith("/_api/"):
            endpoint = f"/_api/{endpoint.lstrip('/')}"
            
        return urljoin(self.base_url, endpoint)
    
    # SharePoint-specific API methods
    async def get_sites(self, filter_expr: str = None) -> List[Dict[str, Any]]:
        """Get SharePoint sites."""
        endpoint = "search/query"
        params = {
            "querytext": "contentclass:STS_Site",
            "selectproperties": "Title,Path,SiteId,WebId,WebTemplate",
            "rowlimit": 500
        }
        
        if filter_expr:
            params["querytext"] += f" AND {filter_expr}"
            
        response = await self.get(endpoint, params)
        
        # Extract sites from search results
        sites = []
        if "PrimaryQueryResult" in response:
            rows = response["PrimaryQueryResult"]["RelevantResults"]["Table"]["Rows"]
            for row in rows:
                site_data = {}
                for cell in row["Cells"]:
                    key = cell["Key"].lower()
                    site_data[key] = cell["Value"]
                sites.append(site_data)
        
        return sites
    
    async def get_site_libraries(self, site_url: str) -> List[Dict[str, Any]]:
        """Get document libraries for a site."""
        endpoint = f"web/lists"
        params = {
            "$filter": "BaseType eq 1 and Hidden eq false",  # Document libraries only
            "$select": "Id,Title,Description,ItemCount,Created,LastItemModifiedDate"
        }
        
        # Switch context to specific site
        original_base = self.base_url
        self.base_url = site_url
        
        try:
            response = await self.get(endpoint, params)
            return response.get("value", [])
        finally:
            self.base_url = original_base
```

## 2. Processing Modules

### 2.1 Document Processor

```python
# packages/qdrant-loader/src/qdrant_loader/connectors/sharepoint/processors/document_processor.py

from typing import List, Dict, Any
from qdrant_loader.connectors.sharepoint.client import SharePointClient
from qdrant_loader.connectors.sharepoint.config import SharePointConfig
from qdrant_loader.core.document import Document
from qdrant_loader.config.types import SourceType
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class DocumentProcessor:
    """Processes SharePoint documents and files."""
    
    def __init__(self, client: SharePointClient, config: SharePointConfig):
        self.client = client
        self.config = config
        
    async def process_site_libraries(self, site: Dict[str, Any]) -> List[Document]:
        """Process all document libraries in a site."""
        site_url = site.get("url", "")
        site_title = site.get("title", "Unknown Site")
        
        documents = []
        
        try:
            # Get document libraries
            libraries = await self.client.get_site_libraries(site_url)
            logger.debug(f"Found {len(libraries)} libraries in {site_title}")
            
            # Process each library
            for library in libraries:
                library_docs = await self._process_library(site, library)
                documents.extend(library_docs)
                
        except Exception as e:
            logger.error(f"Error processing libraries for {site_title}: {e}")
            
        return documents
    
    async def _process_library(
        self, 
        site: Dict[str, Any], 
        library: Dict[str, Any]
    ) -> List[Document]:
        """Process documents in a specific library."""
        library_title = library.get("Title", "Unknown Library")
        library_id = library.get("Id", "")
        
        documents = []
        
        try:
            # Get library items
            items = await self._get_library_items(site, library_id)
            
            # Process each item
            for item in items:
                if self._should_process_item(item):
                    doc = await self._create_document_from_item(site, library, item)
                    if doc:
                        documents.append(doc)
                        
        except Exception as e:
            logger.error(f"Error processing library {library_title}: {e}")
            
        return documents
    
    async def _get_library_items(
        self, 
        site: Dict[str, Any], 
        library_id: str
    ) -> List[Dict[str, Any]]:
        """Get items from a document library."""
        site_url = site.get("url", "")
        
        endpoint = f"web/lists('{library_id}')/items"
        params = {
            "$expand": "File,Folder,FieldValuesAsText",
            "$select": "Id,Title,Created,Modified,Author/Title,Editor/Title,File/Name,File/Size,File/TimeCreated,File/TimeLastModified,FileSystemObjectType,FieldValuesAsText",
            "$top": 5000
        }
        
        # Switch context to site
        original_base = self.client.base_url
        self.client.base_url = site_url
        
        try:
            response = await self.client.get(endpoint, params)
            return response.get("value", [])
        finally:
            self.client.base_url = original_base
    
    def _should_process_item(self, item: Dict[str, Any]) -> bool:
        """Determine if an item should be processed."""
        # Skip folders
        if item.get("FileSystemObjectType") == 1:
            return False
            
        # Check file size limit
        file_info = item.get("File", {})
        file_size = file_info.get("Size", 0)
        max_size_bytes = self.config.max_file_size_mb * 1024 * 1024
        
        if file_size > max_size_bytes:
            logger.debug(f"Skipping large file: {file_info.get('Name')} ({file_size} bytes)")
            return False
        
        # Check file type
        file_name = file_info.get("Name", "")
        file_extension = file_name.split(".")[-1].lower() if "." in file_name else ""
        
        if file_extension not in self.config.supported_file_types:
            logger.debug(f"Skipping unsupported file type: {file_name}")
            return False
            
        return True
    
    async def _create_document_from_item(
        self, 
        site: Dict[str, Any], 
        library: Dict[str, Any], 
        item: Dict[str, Any]
    ) -> Document:
        """Create Document object from SharePoint item."""
        try:
            # Extract basic information
            file_info = item.get("File", {})
            file_name = file_info.get("Name", item.get("Title", "Untitled"))
            
            # Build URL
            site_url = site.get("url", "")
            file_server_relative_url = file_info.get("ServerRelativeUrl", "")
            file_url = f"{site_url}{file_server_relative_url}" if file_server_relative_url else ""
            
            # Extract content (placeholder - would integrate with file conversion)
            content = await self._extract_file_content(site, item)
            
            # Build metadata
            metadata = self._build_item_metadata(site, library, item)
            
            # Create document
            document = Document(
                title=file_name,
                content=content,
                content_type=self._get_content_type(file_name),
                metadata=metadata,
                source_type=SourceType.SHAREPOINT,
                source=self.config.source,
                url=file_url,
                created_at=self._parse_datetime(item.get("Created")),
                updated_at=self._parse_datetime(item.get("Modified"))
            )
            
            return document
            
        except Exception as e:
            logger.error(f"Error creating document from item: {e}")
            return None
```

## 3. Integration Points

### 3.1 MCP Server Tools

```python
# packages/qdrant-loader-mcp-server/src/qdrant_loader_mcp_server/tools/sharepoint.py

from typing import Dict, Any, List
from qdrant_loader_mcp_server.tools.base import BaseTool


class SharePointSearchTool(BaseTool):
    """Search SharePoint content with enhanced filters."""
    
    name = "sharepoint_search"
    description = "Search SharePoint content with site, library, and content type filters"
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute SharePoint-specific search."""
        query = kwargs.get("query", "")
        site_filter = kwargs.get("site", None)
        library_filter = kwargs.get("library", None)
        content_type = kwargs.get("content_type", None)
        
        # Build enhanced search filters
        filters = {}
        if site_filter:
            filters["metadata.site"] = site_filter
        if library_filter:
            filters["metadata.library"] = library_filter
        if content_type:
            filters["metadata.content_type"] = content_type
            
        # Execute search with SharePoint-specific ranking
        results = await self.search_engine.search(
            query=query,
            filters=filters,
            limit=kwargs.get("limit", 10)
        )
        
        # Enhance results with SharePoint context
        enhanced_results = []
        for result in results:
            enhanced_result = {
                **result,
                "sharepoint_context": {
                    "site": result.get("metadata", {}).get("site"),
                    "library": result.get("metadata", {}).get("library"),
                    "author": result.get("metadata", {}).get("author"),
                    "last_modified": result.get("metadata", {}).get("modified"),
                    "permissions": result.get("metadata", {}).get("permissions", [])
                }
            }
            enhanced_results.append(enhanced_result)
        
        return {
            "results": enhanced_results,
            "total": len(enhanced_results),
            "filters_applied": filters
        }


class SharePointSyncTool(BaseTool):
    """Trigger SharePoint synchronization."""
    
    name = "sharepoint_sync"
    description = "Trigger incremental or full SharePoint synchronization"
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute SharePoint sync operation."""
        sync_type = kwargs.get("type", "incremental")  # incremental or full
        site_filter = kwargs.get("site", None)
        
        # Implementation would trigger the actual sync process
        # This is a placeholder for the actual implementation
        
        return {
            "sync_initiated": True,
            "sync_type": sync_type,
            "site_filter": site_filter,
            "estimated_duration": "10-30 minutes"
        }
```

### 3.2 Configuration Integration

```yaml
# Example configuration integration
sources:
  sharepoint:
    - source_type: "sharepoint"
      source: "company-sharepoint"
      base_url: "https://company.sharepoint.com"
      
      # Authentication
      auth_method: "service_principal"
      tenant_id: "${SHAREPOINT_TENANT_ID}"
      client_id: "${SHAREPOINT_CLIENT_ID}"
      client_secret: "${SHAREPOINT_CLIENT_SECRET}"
      
      # Discovery
      discovery_scope: "tenant"
      include_subsites: true
      max_sites: 500
      
      # Content processing
      include_document_libraries: true
      include_pages: true
      include_lists: false
      enable_file_conversion: true
      download_attachments: true
      max_file_size_mb: 50
      
      # Performance
      max_concurrent_requests: 3
      rate_limit_rpm: 300
      enable_incremental_sync: true
      
      # Enhanced features
      enable_enhanced_metadata: true
      enable_analytics: false
      enable_permission_tracking: true
```

## 4. Testing Framework

### 4.1 Unit Tests

```python
# tests/unit/connectors/sharepoint/test_connector.py

import pytest
from unittest.mock import AsyncMock, Mock, patch
from qdrant_loader.connectors.sharepoint.connector import SharePointConnector
from qdrant_loader.connectors.sharepoint.config import SharePointConfig, AuthMethod


class TestSharePointConnector:
    """Unit tests for SharePoint connector."""
    
    @pytest.fixture
    def sharepoint_config(self):
        """Create test SharePoint configuration."""
        return SharePointConfig(
            source_type="sharepoint",
            source="test-sharepoint",
            base_url="https://test.sharepoint.com",
            auth_method=AuthMethod.SERVICE_PRINCIPAL,
            tenant_id="test-tenant",
            client_id="test-client",
            client_secret="test-secret",
            discovery_scope="specific_sites",
            specific_sites=["https://test.sharepoint.com/sites/test"]
        )
    
    @pytest.fixture
    def mock_authenticator(self):
        """Mock SharePoint authenticator."""
        mock = AsyncMock()
        mock.get_access_token.return_value = "mock-token"
        return mock
    
    @pytest.fixture
    def mock_client(self):
        """Mock SharePoint client."""
        mock = AsyncMock()
        mock.get_sites.return_value = [
            {
                "url": "https://test.sharepoint.com/sites/test",
                "title": "Test Site",
                "id": "test-site-id"
            }
        ]
        mock.get_site_libraries.return_value = [
            {
                "Id": "lib-id",
                "Title": "Documents",
                "ItemCount": 5
            }
        ]
        return mock
    
    @pytest.mark.asyncio
    async def test_connector_initialization(self, sharepoint_config):
        """Test connector initialization."""
        with patch.multiple(
            'qdrant_loader.connectors.sharepoint.connector',
            SharePointAuthenticator=Mock(),
            SharePointClient=Mock()
        ):
            connector = SharePointConnector(sharepoint_config)
            assert connector.config == sharepoint_config
            assert connector._processed_items == 0
    
    @pytest.mark.asyncio
    async def test_get_documents(self, sharepoint_config, mock_authenticator, mock_client):
        """Test document retrieval."""
        with patch.multiple(
            'qdrant_loader.connectors.sharepoint.connector',
            SharePointAuthenticator=Mock(return_value=mock_authenticator),
            SharePointClient=Mock(return_value=mock_client)
        ):
            connector = SharePointConnector(sharepoint_config)
            
            # Mock processors
            connector.document_processor.process_site_libraries = AsyncMock(
                return_value=[Mock(title="Test Document")]
            )
            connector.page_processor.process_site_pages = AsyncMock(return_value=[])
            connector.list_processor.process_site_lists = AsyncMock(return_value=[])
            
            async with connector:
                documents = await connector.get_documents()
                
            assert len(documents) > 0
            assert connector._processed_items > 0
```

### 4.2 Integration Tests

```python
# tests/integration/connectors/sharepoint/test_integration.py

import pytest
import os
from qdrant_loader.connectors.sharepoint.connector import SharePointConnector
from qdrant_loader.connectors.sharepoint.config import SharePointConfig, AuthMethod


@pytest.mark.integration
@pytest.mark.asyncio
class TestSharePointIntegration:
    """Integration tests for SharePoint connector."""
    
    @pytest.fixture
    def integration_config(self):
        """Create integration test configuration."""
        return SharePointConfig(
            source_type="sharepoint",
            source="integration-test",
            base_url=os.environ.get("TEST_SHAREPOINT_URL"),
            auth_method=AuthMethod.SERVICE_PRINCIPAL,
            tenant_id=os.environ.get("TEST_SHAREPOINT_TENANT_ID"),
            client_id=os.environ.get("TEST_SHAREPOINT_CLIENT_ID"),
            client_secret=os.environ.get("TEST_SHAREPOINT_CLIENT_SECRET"),
            discovery_scope="specific_sites",
            specific_sites=[os.environ.get("TEST_SHAREPOINT_SITE_URL")],
            max_sites=5,
            max_concurrent_requests=2
        )
    
    @pytest.mark.skipif(
        not all([
            os.environ.get("TEST_SHAREPOINT_URL"),
            os.environ.get("TEST_SHAREPOINT_TENANT_ID"),
            os.environ.get("TEST_SHAREPOINT_CLIENT_ID"),
            os.environ.get("TEST_SHAREPOINT_CLIENT_SECRET")
        ]),
        reason="SharePoint integration test environment not configured"
    )
    async def test_real_sharepoint_connection(self, integration_config):
        """Test connection to real SharePoint environment."""
        connector = SharePointConnector(integration_config)
        
        async with connector:
            # Test basic connectivity
            sites = await connector._discover_sites()
            assert len(sites) > 0
            
            # Test document retrieval (limited)
            documents = await connector.get_documents()
            assert isinstance(documents, list)
            
            # Verify document structure
            if documents:
                doc = documents[0]
                assert hasattr(doc, 'title')
                assert hasattr(doc, 'content')
                assert hasattr(doc, 'metadata')
                assert doc.source_type == "sharepoint"
```

## 5. Deployment Considerations

### 5.1 Environment Setup

```bash
# Environment variables for SharePoint connector
export SHAREPOINT_TENANT_ID="your-tenant-id"
export SHAREPOINT_CLIENT_ID="your-app-id"
export SHAREPOINT_CLIENT_SECRET="your-client-secret"

# Optional: Certificate-based auth
export SHAREPOINT_CERT_PATH="/path/to/certificate.pfx"
export SHAREPOINT_CERT_PASSWORD="certificate-password"

# Rate limiting
export SHAREPOINT_RATE_LIMIT_RPM="600"
export SHAREPOINT_RATE_LIMIT_RPH="10000"

# Monitoring
export SHAREPOINT_LOG_LEVEL="INFO"
export SHAREPOINT_ENABLE_METRICS="true"
```

### 5.2 Docker Integration

```dockerfile
# Dockerfile additions for SharePoint connector
FROM python:3.11-slim

# Install additional dependencies for SharePoint
RUN pip install \
    msal==1.20.0 \
    cryptography==41.0.0 \
    httpx[http2]==0.24.0

# Copy SharePoint connector files
COPY packages/qdrant-loader/src/qdrant_loader/connectors/sharepoint /app/qdrant_loader/connectors/sharepoint

# Environment variables
ENV SHAREPOINT_LOG_LEVEL=INFO
ENV SHAREPOINT_RATE_LIMIT_RPM=600
```

### 5.3 Monitoring Setup

```python
# Monitoring integration
class SharePointMetrics:
    """SharePoint-specific metrics collection."""
    
    def __init__(self):
        self.sites_processed = 0
        self.documents_processed = 0
        self.errors_count = 0
        self.api_calls_count = 0
        self.processing_times = []
    
    def record_site_processed(self):
        self.sites_processed += 1
    
    def record_document_processed(self):
        self.documents_processed += 1
    
    def record_error(self, error_type: str):
        self.errors_count += 1
    
    def record_api_call(self):
        self.api_calls_count += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        return {
            "sites_processed": self.sites_processed,
            "documents_processed": self.documents_processed,
            "errors_count": self.errors_count,
            "api_calls_count": self.api_calls_count,
            "avg_processing_time": sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
        }
```

This implementation guide provides the foundation for building a robust SharePoint connector that integrates seamlessly with the existing QDrant Loader architecture while providing enterprise-grade features and reliability. 