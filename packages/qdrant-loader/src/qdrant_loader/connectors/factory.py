from typing import Any

from .registry import CONNECTOR_REGISTRY


def get_connector_instance(config: Any, checkpoint_cursor: str | None = None) -> Any:
    """Create and return a connector instance based on the config's source and deployment type.

    Accepts an optional `checkpoint_cursor` which will be passed to connector
    implementations that support resumption (e.g., Jira connectors). If the
    connector class does not accept the extra parameter, the function falls
    back to constructing it with the single `config` argument for
    backward-compatibility.
    """
    key = (config.source_type, getattr(config, "deployment_type", None))

    connector_class = CONNECTOR_REGISTRY.get(key)

    if not connector_class:
        raise ValueError(f"Unsupported connector type: {key}")

    # Try to construct with checkpoint_cursor kwarg; fall back to single-arg.
    try:
        # Prefer keyword to be explicit; works for connectors that declare
        # `checkpoint_cursor` as a parameter (positional or keyword).
        return connector_class(config, checkpoint_cursor=checkpoint_cursor)
    except TypeError:
        # Connector likely doesn't accept the extra arg – fall back.
        return connector_class(config)
