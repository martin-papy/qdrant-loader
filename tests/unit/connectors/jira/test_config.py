"""Tests for Jira configuration."""

import os
import pytest
from pydantic import ValidationError
from qdrant_loader.connectors.jira.config import JiraConfig

@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Set up mock environment variables."""
    monkeypatch.setenv("JIRA_TOKEN", "test_token")
    monkeypatch.setenv("JIRA_EMAIL", "test@example.com")
    yield
    # Cleanup is handled automatically by monkeypatch

def test_valid_config(mock_env_vars):
    """Test creating a valid JiraConfig."""
    config = JiraConfig(
        base_url="https://test.atlassian.net",
        project_key="TEST",
        requests_per_minute=60,
        page_size=100,
        process_attachments=True,
        track_last_sync=True,
    )
    assert str(config.base_url) == "https://test.atlassian.net/"
    assert config.project_key == "TEST"
    assert config.requests_per_minute == 60
    assert config.page_size == 100
    assert config.process_attachments is True
    assert config.track_last_sync is True
    assert config.api_token == "test_token"
    assert config.email == "test@example.com"

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

def test_default_values(mock_env_vars):
    """Test JiraConfig default values."""
    config = JiraConfig(
        base_url="https://test.atlassian.net",
        project_key="TEST",
    )
    assert str(config.base_url) == "https://test.atlassian.net/"
    assert config.project_key == "TEST"
    assert config.requests_per_minute == 60  # default value
    assert config.page_size == 100  # default value
    assert config.process_attachments is True  # default value
    assert config.track_last_sync is True  # default value
    assert config.issue_types == []  # default value
    assert config.include_statuses == []  # default value
    assert config.api_token == "test_token"  # from env var
    assert config.email == "test@example.com"  # from env var

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