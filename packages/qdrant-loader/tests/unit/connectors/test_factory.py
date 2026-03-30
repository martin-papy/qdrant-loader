from unittest.mock import patch

import pytest
from qdrant_loader.connectors.factory import get_connector_instance


class DummyConfig:
    def __init__(self, source_type, deployment_type):
        self.source_type = source_type
        self.deployment_type = deployment_type


class DummyConnector:
    def __init__(self, config):
        self.config = config


def test_get_connector_instance_success():
    """Test that a connector instance is correctly created for a valid configuration."""
    config = DummyConfig("jira", "cloud")

    mock_registry = {("jira", "cloud"): DummyConnector}

    with patch("qdrant_loader.connectors.factory.CONNECTOR_REGISTRY", mock_registry):
        connector = get_connector_instance(config)

        assert isinstance(connector, DummyConnector)
        assert connector.config == config


def test_get_connector_instance_without_deployment_type():
    """Test that the correct connector instance is returned when deployment type is not provided."""
    config = DummyConfig("publicdocs", None)

    mock_registry = {("publicdocs", None): DummyConnector}

    with patch("qdrant_loader.connectors.factory.CONNECTOR_REGISTRY", mock_registry):
        connector = get_connector_instance(config)

        assert isinstance(connector, DummyConnector)


def test_get_connector_instance_unsupported_deployment_type():
    """Test that an error is raised for an unsupported deployment type."""
    config = DummyConfig("jira", "server")

    mock_registry = {("jira", "cloud"): DummyConnector}

    with patch("qdrant_loader.connectors.factory.CONNECTOR_REGISTRY", mock_registry):
        with pytest.raises(ValueError) as exc_info:
            get_connector_instance(config)

        assert "Unsupported connector type" in str(exc_info.value)
