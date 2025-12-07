"""SharePoint connector package for qdrant-loader.

This connector uses Microsoft Graph API via GraphClient to ingest
documents from SharePoint Online document libraries.

Example:
    from qdrant_loader.connectors.sharepoint import SharePointConnector, SharePointConfig

    config = SharePointConfig(
        source="my-site",
        source_type="sharepoint",
        base_url="https://company.sharepoint.com",
        site_url="https://company.sharepoint.com/sites/mysite",
        relative_url="/sites/mysite",
        tenant_id="your-tenant-id",
        client_id="your-client-id",
        client_secret="your-client-secret",
    )

    async with SharePointConnector(config) as connector:
        documents = await connector.get_documents()
"""

from qdrant_loader.connectors.sharepoint.auth import (
    SharePointAuthError,
    create_graph_client,
    get_site_by_url,
    validate_connection,
)
from qdrant_loader.connectors.sharepoint.config import (
    SharePointAuthMethod,
    SharePointConfig,
)
from qdrant_loader.connectors.sharepoint.connector import SharePointConnector
from qdrant_loader.connectors.sharepoint.file_processor import SharePointFileProcessor
from qdrant_loader.connectors.sharepoint.metadata_extractor import (
    SharePointMetadataExtractor,
)

__all__ = [
    # Main connector
    "SharePointConnector",
    # Config
    "SharePointConfig",
    "SharePointAuthMethod",
    # Auth functions
    "create_graph_client",
    "validate_connection",
    "get_site_by_url",
    "SharePointAuthError",
    # Processing classes
    "SharePointFileProcessor",
    "SharePointMetadataExtractor",
]