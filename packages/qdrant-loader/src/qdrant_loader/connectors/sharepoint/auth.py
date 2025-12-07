"""SharePoint authentication using Microsoft Graph API.

This module provides function-based authentication using GraphClient from
office365-rest-python-client library.

Authentication Methods:
- CLIENT_CREDENTIALS: GraphClient(tenant=tenant).with_client_secret(client_id, client_secret)
- USER_CREDENTIALS: GraphClient(tenant=tenant).with_username_and_password(client_id, username, password)

Note: Office365-REST-Python-Client handles token refresh automatically.

Reference:
- examples/auth/with_client_secret.py
- examples/auth/with_user_creds.py
"""

from office365.graph_client import GraphClient

from qdrant_loader.connectors.sharepoint.config import (
    SharePointAuthMethod,
    SharePointConfig,
)
from qdrant_loader.utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class SharePointAuthError(Exception):
    """Authentication error for SharePoint."""

    pass


def create_graph_client(config: SharePointConfig) -> GraphClient:
    """Create authenticated GraphClient for Microsoft Graph API.

    Uses built-in authentication methods from office365-rest-python-client:
    - CLIENT_CREDENTIALS: GraphClient(tenant=tenant).with_client_secret(client_id, client_secret)
    - USER_CREDENTIALS: GraphClient(tenant=tenant).with_username_and_password(client_id, username, password)

    Note: Office365-REST-Python-Client handles token refresh automatically.

    Args:
        config: SharePoint configuration

    Returns:
        Authenticated GraphClient

    Raises:
        SharePointAuthError: If authentication fails
    """
    if not config.tenant_id:
        raise SharePointAuthError("tenant_id is required for authentication")

    if config.auth_method == SharePointAuthMethod.CLIENT_CREDENTIALS:
        if not config.client_id or not config.client_secret:
            raise SharePointAuthError(
                "client_id and client_secret required for client_credentials auth"
            )

        # Built-in method from office365-rest-python-client
        # Reference: examples/auth/with_client_secret.py
        client = GraphClient(tenant=config.tenant_id).with_client_secret(
            config.client_id, config.client_secret
        )

    elif config.auth_method == SharePointAuthMethod.USER_CREDENTIALS:
        if not config.client_id or not config.username or not config.password:
            raise SharePointAuthError(
                "client_id, username and password required for user_credentials auth"
            )

        # Built-in method from office365-rest-python-client
        # Reference: examples/auth/with_user_creds.py
        # Note: ROPC flow - does NOT work with MFA-enabled accounts
        client = GraphClient(tenant=config.tenant_id).with_username_and_password(
            config.client_id, config.username, config.password
        )

    else:
        raise SharePointAuthError(f"Unsupported auth method: {config.auth_method}")

    logger.debug(
        "GraphClient created",
        auth_method=config.auth_method.value,
        tenant_id=config.tenant_id,
    )

    return client


def validate_connection(client: GraphClient) -> dict:
    """Validate connection by fetching root site info.

    Args:
        client: Authenticated GraphClient

    Returns:
        Dict with site info (display_name, web_url)

    Raises:
        SharePointAuthError: If validation fails
    """
    try:
        # Get root site to validate connection
        root_site = client.sites.root.get().execute_query()

        # Site object properties may vary - use safe access
        # Possible attributes: display_name, displayName, name, web_url, webUrl
        display_name = (
            getattr(root_site, "display_name", None)
            or getattr(root_site, "displayName", None)
            or getattr(root_site, "name", None)
            or "Unknown"
        )

        web_url = (
            getattr(root_site, "web_url", None)
            or getattr(root_site, "webUrl", None)
            or str(root_site)
            or ""
        )

        site_info = {
            "display_name": display_name,
            "web_url": web_url,
        }

        logger.info(
            "SharePoint connection validated",
            site_name=site_info["display_name"],
            site_url=site_info["web_url"],
        )

        return site_info

    except SharePointAuthError:
        # Re-raise our own errors without wrapping
        raise
    except Exception as e:
        error_str = str(e).lower()
        if "401" in error_str or "unauthorized" in error_str:
            raise SharePointAuthError(
                "Authentication failed - invalid credentials"
            ) from e
        elif "403" in error_str or "forbidden" in error_str:
            raise SharePointAuthError("Access denied - check permissions") from e
        elif "404" in error_str:
            raise SharePointAuthError("Site not found - check tenant_id") from e
        else:
            raise SharePointAuthError(f"Connection validation failed: {e}") from e


def get_site_by_url(client: GraphClient, host: str, site_path: str):
    """Get SharePoint site by URL.

    Args:
        client: Authenticated GraphClient
        host: SharePoint host (e.g., "company.sharepoint.com")
        site_path: Site relative path (e.g., "/sites/mysite")

    Returns:
        Site object

    Example:
        site = get_site_by_url(client, "company.sharepoint.com", "/sites/mysite")
    """
    # Format: host:/path - as documented in Microsoft Graph API
    site_url = f"{host}:{site_path}"
    site = client.sites.get_by_url(site_url).execute_query()
    return site
