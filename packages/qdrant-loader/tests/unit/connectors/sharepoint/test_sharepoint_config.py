import os
from unittest.mock import patch
import pytest
import yaml
from pathlib import Path
from qdrant_loader.connectors.sharepoint.config import SharePointConfig, SharePointAuthMethod

@pytest.fixture
def mock_env_vars():
    """Set up mock environment variables for SharePoint config."""
    with patch.dict(
        os.environ,
        {
        "SHAREPOINT_CLIENT_ID": "CLIENT123",
        "SHAREPOINT_CLIENT_SECRET": "SECRET123",
        "SHAREPOINT_TENANT_ID": "TENANT123",
        }
    ):
        yield

def test_sharepoint_config_client_credentials(mock_env_vars):
    config_path = Path("tests/config.test.yaml")

    with open(config_path) as f:
        raw = yaml.safe_load(f)

        sp = (
            raw["projects"]
            ["theorcs"]
            ["sources"]
            ["sharepoint"]
            ["intranet"]
        )

    config = SharePointConfig(**sp)
    assert config.tenant_id == "TENANT123"

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
