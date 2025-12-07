"""Unit tests for SharePoint authentication module.

Tests function-based authentication using GraphClient from office365-rest-python-client.
"""

import pytest
from unittest.mock import patch, MagicMock

from qdrant_loader.connectors.sharepoint.auth import (
    create_graph_client,
    validate_connection,
    get_site_by_url,
    SharePointAuthError,
)
from qdrant_loader.connectors.sharepoint.config import (
    SharePointConfig,
    SharePointAuthMethod,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def client_credentials_config():
    """Create SharePointConfig with client credentials auth."""
    return SharePointConfig(
        source="test-sharepoint",
        source_type="sharepoint",
        base_url="https://company.sharepoint.com",
        site_url="https://company.sharepoint.com/sites/test-site",
        relative_url="/sites/test-site",
        auth_method=SharePointAuthMethod.CLIENT_CREDENTIALS,
        tenant_id="12345678-1234-1234-1234-123456789012",
        client_id="client-app-id",
        client_secret="client-secret-value",
    )


@pytest.fixture
def user_credentials_config():
    """Create SharePointConfig with user credentials auth."""
    return SharePointConfig(
        source="test-sharepoint",
        source_type="sharepoint",
        base_url="https://company.sharepoint.com",
        site_url="https://company.sharepoint.com/sites/test-site",
        relative_url="/sites/test-site",
        auth_method=SharePointAuthMethod.USER_CREDENTIALS,
        tenant_id="12345678-1234-1234-1234-123456789012",
        client_id="client-app-id",
        username="user@company.com",
        password="user-password",
    )


@pytest.fixture
def mock_graph_client():
    """Mock GraphClient class."""
    with patch("qdrant_loader.connectors.sharepoint.auth.GraphClient") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        mock_instance.with_client_secret.return_value = mock_instance
        mock_instance.with_username_and_password.return_value = mock_instance
        yield mock


# =============================================================================
# Test create_graph_client
# =============================================================================


class TestCreateGraphClient:
    """Tests for create_graph_client function."""

    def test_client_credentials_auth_success(
        self, client_credentials_config, mock_graph_client
    ):
        """Test successful client credentials authentication."""
        client = create_graph_client(client_credentials_config)

        # Verify GraphClient was created with tenant
        mock_graph_client.assert_called_once_with(
            tenant=client_credentials_config.tenant_id
        )

        # Verify with_client_secret was called
        mock_graph_client.return_value.with_client_secret.assert_called_once_with(
            client_credentials_config.client_id,
            client_credentials_config.client_secret,
        )

        assert client is not None

    def test_user_credentials_auth_success(
        self, user_credentials_config, mock_graph_client
    ):
        """Test successful user credentials authentication."""
        client = create_graph_client(user_credentials_config)

        # Verify GraphClient was created with tenant
        mock_graph_client.assert_called_once_with(
            tenant=user_credentials_config.tenant_id
        )

        # Verify with_username_and_password was called
        mock_graph_client.return_value.with_username_and_password.assert_called_once_with(
            user_credentials_config.client_id,
            user_credentials_config.username,
            user_credentials_config.password,
        )

        assert client is not None

    def test_missing_tenant_id_raises_error(self, client_credentials_config):
        """Test that missing tenant_id raises SharePointAuthError."""
        client_credentials_config.tenant_id = None

        with pytest.raises(SharePointAuthError, match="tenant_id is required"):
            create_graph_client(client_credentials_config)

    def test_missing_client_secret_raises_error(
        self, client_credentials_config, mock_graph_client
    ):
        """Test that missing client_secret raises SharePointAuthError."""
        client_credentials_config.client_secret = None

        with pytest.raises(SharePointAuthError, match="client_id and client_secret"):
            create_graph_client(client_credentials_config)

    def test_missing_client_id_raises_error(
        self, client_credentials_config, mock_graph_client
    ):
        """Test that missing client_id raises SharePointAuthError."""
        client_credentials_config.client_id = None

        with pytest.raises(SharePointAuthError, match="client_id and client_secret"):
            create_graph_client(client_credentials_config)

    def test_user_auth_missing_username_raises_error(
        self, user_credentials_config, mock_graph_client
    ):
        """Test that missing username raises SharePointAuthError."""
        user_credentials_config.username = None

        with pytest.raises(
            SharePointAuthError, match="client_id, username and password"
        ):
            create_graph_client(user_credentials_config)

    def test_user_auth_missing_password_raises_error(
        self, user_credentials_config, mock_graph_client
    ):
        """Test that missing password raises SharePointAuthError."""
        user_credentials_config.password = None

        with pytest.raises(
            SharePointAuthError, match="client_id, username and password"
        ):
            create_graph_client(user_credentials_config)


# =============================================================================
# Test validate_connection
# =============================================================================


class TestValidateConnection:
    """Tests for validate_connection function."""

    def test_validate_connection_success(self):
        """Test successful connection validation."""
        mock_client = MagicMock()
        mock_site = MagicMock()
        mock_site.display_name = "Test Site"
        mock_site.web_url = "https://company.sharepoint.com/sites/test"
        mock_client.sites.root.get.return_value.execute_query.return_value = mock_site

        result = validate_connection(mock_client)

        assert result["display_name"] == "Test Site"
        assert result["web_url"] == "https://company.sharepoint.com/sites/test"

    def test_validate_connection_401_error(self):
        """Test 401 unauthorized error handling."""
        mock_client = MagicMock()
        mock_client.sites.root.get.return_value.execute_query.side_effect = Exception(
            "401 Unauthorized"
        )

        with pytest.raises(SharePointAuthError, match="invalid credentials"):
            validate_connection(mock_client)

    def test_validate_connection_403_error(self):
        """Test 403 forbidden error handling."""
        mock_client = MagicMock()
        mock_client.sites.root.get.return_value.execute_query.side_effect = Exception(
            "403 Forbidden"
        )

        with pytest.raises(SharePointAuthError, match="Access denied"):
            validate_connection(mock_client)

    def test_validate_connection_404_error(self):
        """Test 404 not found error handling."""
        mock_client = MagicMock()
        mock_client.sites.root.get.return_value.execute_query.side_effect = Exception(
            "404 Not Found"
        )

        with pytest.raises(SharePointAuthError, match="Site not found"):
            validate_connection(mock_client)

    def test_validate_connection_generic_error(self):
        """Test generic error handling."""
        mock_client = MagicMock()
        mock_client.sites.root.get.return_value.execute_query.side_effect = Exception(
            "Network error"
        )

        with pytest.raises(SharePointAuthError, match="Connection validation failed"):
            validate_connection(mock_client)

    def test_validate_connection_empty_site_info(self):
        """Test handling of empty site info."""
        mock_client = MagicMock()
        mock_site = MagicMock()
        mock_site.display_name = None
        mock_site.web_url = None
        mock_client.sites.root.get.return_value.execute_query.return_value = mock_site

        result = validate_connection(mock_client)

        assert result["display_name"] == "Unknown"
        assert result["web_url"] == ""


# =============================================================================
# Test get_site_by_url
# =============================================================================


class TestGetSiteByUrl:
    """Tests for get_site_by_url function."""

    def test_get_site_by_url_success(self):
        """Test successful site retrieval by URL."""
        mock_client = MagicMock()
        mock_site = MagicMock()
        mock_client.sites.get_by_url.return_value.execute_query.return_value = mock_site

        result = get_site_by_url(
            mock_client, "company.sharepoint.com", "/sites/test-site"
        )

        mock_client.sites.get_by_url.assert_called_once_with(
            "company.sharepoint.com:/sites/test-site"
        )
        assert result == mock_site

    def test_get_site_by_url_format(self):
        """Test that site URL is formatted correctly."""
        mock_client = MagicMock()

        get_site_by_url(mock_client, "tenant.sharepoint.com", "/sites/mysite")

        # Verify the format is host:/path
        mock_client.sites.get_by_url.assert_called_with(
            "tenant.sharepoint.com:/sites/mysite"
        )


# =============================================================================
# Test SharePointAuthError
# =============================================================================


class TestSharePointAuthError:
    """Tests for SharePointAuthError exception."""

    def test_auth_error_message(self):
        """Test error message is preserved."""
        error = SharePointAuthError("Test error message")
        assert str(error) == "Test error message"

    def test_auth_error_inheritance(self):
        """Test that SharePointAuthError is an Exception."""
        error = SharePointAuthError("Test")
        assert isinstance(error, Exception)
