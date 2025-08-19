from __future__ import annotations

from typing import Any


def flatten_metadata_components(metadata_components: dict[str, Any]) -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for _component_name, component in metadata_components.items():
        if component is None:
            continue
        if hasattr(component, "__dict__"):
            for key, value in component.__dict__.items():
                flattened[key] = value
        elif isinstance(component, dict):
            flattened.update(component)
    return flattened


