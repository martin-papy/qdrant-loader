import pytest
from pydantic import ValidationError
from qdrant_loader.connectors.sharepoint.config import SharePointConfig, SharePointAuthMethod
import os


class TestSharePointConfig:

    def test_valid_config_client_credentials(self):
        """Test valid config with client credentials."""
        config = SharePointConfig(
            source="test",
            source_type="sharepoint",
            base_url="https://company.sharepoint.com",
            relative_url="/sites/test",
            tenant_id="12345678-1234-1234-1234-123456789012",
            client_id="client-123",
            client_secret="secret-456",
        )
        assert config.authentication_method == SharePointAuthMethod.CLIENT_CREDENTIALS
        assert config.client_secret == "secret-456"

    def test_missing_client_secret_raises(self):
        """Missing client_secret for CLIENT_CREDENTIALS should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SharePointConfig(
                source="test",
                source_type="sharepoint",
                base_url="https://company.sharepoint.com",
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
            relative_url="/sites/test",
            tenant_id="12345678-1234-1234-1234-123456789012",
            client_id="client-123",
        )
        assert config.client_secret == "env-secret"

    def test_file_extensions_normalized(self):
        """Test file extension normalization."""
        config = SharePointConfig(
            source="test",
            source_type="sharepoint",
            base_url="https://company.sharepoint.com",
            relative_url="/sites/test",
            tenant_id="12345678-1234-1234-1234-123456789012",
            client_id="client-123",
            client_secret="secret-456",
            file_extensions=["pdf", "docx", "md"],
        )
        assert config.file_extensions == ["pdf", "docx", "md"]
