import pytest
from pydantic import ValidationError
from qdrant_loader.connectors.sharepoint.config import SharePointConfig, SharePointAuthMethod


class TestSharePointConfig:

    def test_valid_config_client_credentials(self):
        """Test valid config with client credentials."""
        config = SharePointConfig(
            source="test",
            source_type="sharepoint",
            base_url="https://company.sharepoint.com",
            site_url="https://company.sharepoint.com/sites/test",
            relative_url="/sites/test",
            tenant_id="12345678-1234-1234-1234-123456789012",
            client_id="client-123",
            client_secret="secret-456",
        )
        assert config.auth_method == SharePointAuthMethod.CLIENT_CREDENTIALS
        assert config.client_secret == "secret-456"

    def test_missing_client_secret_raises(self, monkeypatch):
        """Missing client_secret for CLIENT_CREDENTIALS should raise ValidationError."""
        # Ensure env var is not set so it won't be loaded from environment
        monkeypatch.delenv("SHAREPOINT_CLIENT_SECRET", raising=False)
        with pytest.raises(ValidationError) as exc_info:
            SharePointConfig(
                source="test",
                source_type="sharepoint",
                base_url="https://company.sharepoint.com",
                site_url="https://company.sharepoint.com/sites/test",
                relative_url="/sites/test",
                tenant_id="12345678-1234-1234-1234-123456789012",
                client_id="client-123",
            )
        assert "client_secret is required" in str(exc_info.value)

    def test_env_variable_loading(self, monkeypatch):
        """If client_secret is missing, it should load from environment variable."""
        monkeypatch.setenv("SHAREPOINT_CLIENT_SECRET", "env-secret")
        config = SharePointConfig(
            source="test",
            source_type="sharepoint",
            base_url="https://company.sharepoint.com",
            site_url="https://company.sharepoint.com/sites/test",
            relative_url="/sites/test",
            tenant_id="12345678-1234-1234-1234-123456789012",
            client_id="client-123",
        )
        assert config.client_secret == "env-secret"

    def test_file_types_normalized(self):
        """Test file type normalization."""
        config = SharePointConfig(
            source="test",
            source_type="sharepoint",
            base_url="https://company.sharepoint.com",
            site_url="https://company.sharepoint.com/sites/test",
            relative_url="/sites/test",
            tenant_id="12345678-1234-1234-1234-123456789012",
            client_id="client-123",
            client_secret="secret-456",
            file_types=["pdf", "docx", "md"],
        )
        assert config.file_types == ["pdf", "docx", "md"]

    def test_file_types_strips_dots(self):
        """Test file types with leading dots are normalized."""
        config = SharePointConfig(
            source="test",
            source_type="sharepoint",
            base_url="https://company.sharepoint.com",
            site_url="https://company.sharepoint.com/sites/test",
            relative_url="/sites/test",
            tenant_id="12345678-1234-1234-1234-123456789012",
            client_id="client-123",
            client_secret="secret-456",
            file_types=[".pdf", ".DOCX", "  md  "],
        )
        assert config.file_types == ["pdf", "docx", "md"]

    def test_user_credentials_auth(self):
        """Test user credentials authentication."""
        config = SharePointConfig(
            source="test",
            source_type="sharepoint",
            base_url="https://company.sharepoint.com",
            site_url="https://company.sharepoint.com/sites/test",
            relative_url="/sites/test",
            auth_method=SharePointAuthMethod.USER_CREDENTIALS,
            tenant_id="12345678-1234-1234-1234-123456789012",
            client_id="client-123",
            username="user@company.com",
            password="password123",
        )
        assert config.auth_method == SharePointAuthMethod.USER_CREDENTIALS
        assert config.username == "user@company.com"

    def test_user_credentials_missing_username_raises(self, monkeypatch):
        """Missing username for USER_CREDENTIALS should raise ValidationError."""
        monkeypatch.delenv("SHAREPOINT_CLIENT_SECRET", raising=False)
        with pytest.raises(ValidationError) as exc_info:
            SharePointConfig(
                source="test",
                source_type="sharepoint",
                base_url="https://company.sharepoint.com",
                site_url="https://company.sharepoint.com/sites/test",
                relative_url="/sites/test",
                auth_method=SharePointAuthMethod.USER_CREDENTIALS,
                tenant_id="12345678-1234-1234-1234-123456789012",
                client_id="client-123",
                password="password123",
            )
        assert "username is required" in str(exc_info.value)
