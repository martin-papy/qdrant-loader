from __future__ import annotations

from typing import Any
from collections.abc import Mapping
from dataclasses import is_dataclass, asdict


def flatten_metadata_components(metadata_components: dict[str, Any]) -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for _component_name, component in metadata_components.items():
        if component is None:
            continue
        # Dataclasses (supports slots via asdict)
        if is_dataclass(component):
            for key, value in asdict(component).items():
                if isinstance(key, str) and not key.startswith("_") and not callable(value):
                    flattened[key] = value
            continue

        # Generic Mapping (handles dict and subclasses like MappingProxyType)
        try:
            is_mapping = isinstance(component, Mapping)
        except Exception:
            # Some mocked objects with custom __dict__ can raise during isinstance checks
            is_mapping = False
        if is_mapping:
            try:
                items_iter = component.items()  # type: ignore[assignment]
            except Exception:
                items_iter = []
            for key, value in items_iter:
                if isinstance(key, str) and not key.startswith("_") and not callable(value):
                    flattened[key] = value
            continue

        # Fallback: inspect __dict__ but filter out private keys and callables
        if hasattr(component, "__dict__") and isinstance(component.__dict__, dict):
            for key, value in component.__dict__.items():
                if isinstance(key, str) and not key.startswith("_") and not callable(value):
                    flattened[key] = value
    return flattened


