from typing import Any

from .registry import CONNECTOR_REGISTRY


def get_connector_instance(config: Any) -> Any:
    """Create and return a connector instance based on the config's source and deployment type."""
    key = (config.source_type, getattr(config, "deployment_type", None))

    connector_class = CONNECTOR_REGISTRY.get(key)

    if not connector_class:
        raise ValueError(f"Unsupported connector type: {key}")

    return connector_class(config)
