"""Tests for Jira configuration."""

import os
import pytest
from pydantic import ValidationError
from qdrant_loader.connectors.jira.config import JiraConfig
from qdrant_loader.config import Settings
from pathlib import Path

@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Set up mock environment variables."""
    monkeypatch.setenv("JIRA_TOKEN", "${JIRA_TOKEN}")
    monkeypatch.setenv("JIRA_EMAIL", "${JIRA_EMAIL}")
    yield
    # Cleanup is handled automatically by monkeypatch

@pytest.fixture
def test_settings():
    """Load test settings from config file."""
    config_path = Path(__file__).parent.parent.parent.parent / "config.test.yaml"
    if not config_path.exists():
        pytest.fail("Test configuration file not found")
    return Settings.from_yaml(config_path)

def test_valid_config(mock_env_vars, test_settings):
    """Test creating a valid JiraConfig."""
    jira_settings = test_settings.sources_config.jira["test-project"]
    config = JiraConfig(
        base_url=jira_settings.base_url,
        project_key=jira_settings.project_key,
        requests_per_minute=jira_settings.requests_per_minute,
        page_size=jira_settings.page_size,
        process_attachments=jira_settings.process_attachments,
        track_last_sync=jira_settings.track_last_sync,
    )
    assert str(config.base_url) == jira_settings.base_url
    assert config.project_key == jira_settings.project_key
    assert config.requests_per_minute == jira_settings.requests_per_minute
    assert config.page_size == jira_settings.page_size
    assert config.process_attachments == jira_settings.process_attachments
    assert config.track_last_sync == jira_settings.track_last_sync
    assert config.api_token == "${JIRA_TOKEN}"
    assert config.email == "${JIRA_EMAIL}"

def test_invalid_base_url():
    """Test that invalid base URL raises validation error."""
    with pytest.raises(ValidationError):
        JiraConfig(
            base_url="not-a-url",
            project_key="TEST",
            api_token="test_token",
            email="test@example.com"
        )

def test_missing_project_key():
    """Test that missing project key raises validation error."""
    with pytest.raises(ValidationError):
        JiraConfig(
            base_url="https://test.atlassian.net",
            api_token="test_token",
            email="test@example.com"
        )

def test_default_values(mock_env_vars, test_settings):
    """Test JiraConfig default values."""
    jira_settings = test_settings.sources_config.jira["test-project"]
    config = JiraConfig(
        base_url=jira_settings.base_url,
        project_key=jira_settings.project_key,
    )
    assert str(config.base_url) == jira_settings.base_url
    assert config.project_key == jira_settings.project_key
    assert config.requests_per_minute == 60  # default value
    assert config.page_size == 100  # default value
    assert config.process_attachments is True  # default value
    assert config.track_last_sync is True  # default value
    assert config.issue_types == []  # default value
    assert config.include_statuses == []  # default value
    assert config.api_token == "${JIRA_TOKEN}"  # from env var
    assert config.email == "${JIRA_EMAIL}"  # from env var

def test_invalid_requests_per_minute():
    """Test that invalid requests_per_minute raises validation error."""
    with pytest.raises(ValidationError):
        JiraConfig(
            base_url="https://test.atlassian.net",
            project_key="TEST",
            api_token="test_token",
            email="test@example.com",
            requests_per_minute=0
        )

def test_invalid_page_size():
    """Test that invalid page_size raises validation error."""
    with pytest.raises(ValidationError):
        JiraConfig(
            base_url="https://test.atlassian.net",
            project_key="TEST",
            api_token="test_token",
            email="test@example.com",
            page_size=0
        ) 