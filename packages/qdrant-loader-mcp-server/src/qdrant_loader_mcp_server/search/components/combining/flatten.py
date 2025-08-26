from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from typing import Any


def flatten_metadata_components(metadata_components: dict[str, Any]) -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    # Denylist of sensitive key patterns to redact
    sensitive_key_patterns = {"password", "secret", "token", "api_key", "apikey"}

    def _should_include(key: Any, value: Any) -> bool:
        if not isinstance(key, str):
            return False
        if key.startswith("_"):
            return False
        try:
            if callable(value):
                return False
        except Exception:
            # Some objects may raise when inspected for callability
            return False
        return True

    def _maybe_redact(key: str, value: Any) -> Any:
        lower_key = key.lower()
        for pattern in sensitive_key_patterns:
            if pattern in lower_key:
                return "[REDACTED]"
        return value

    for _component_name, component in metadata_components.items():
        if component is None:
            continue
        # Dataclasses (supports slots via asdict)
        if is_dataclass(component):
            for key, value in asdict(component).items():
                if _should_include(key, value):
                    flattened[key] = _maybe_redact(key, value)
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
                if _should_include(key, value):
                    flattened[key] = _maybe_redact(key, value)
            continue

        # Fallback: inspect __dict__ but filter out private keys and callables
        if hasattr(component, "__dict__") and isinstance(component.__dict__, dict):
            for key, value in component.__dict__.items():
                if _should_include(key, value):
                    flattened[key] = _maybe_redact(key, value)

        # Support for objects using __slots__ without a traditional __dict__
        try:
            has_slots = hasattr(component, "__slots__")
        except Exception:
            has_slots = False
        if has_slots:
            try:
                slots = component.__slots__
            except Exception:
                slots = []
            # __slots__ can be a string or an iterable of strings
            slot_names: list[str] = []
            if isinstance(slots, str):
                slot_names = [slots]
            else:
                try:
                    slot_names = [s for s in slots if isinstance(s, str)]  # type: ignore[assignment]
                except Exception:
                    slot_names = []
            for key in slot_names:
                if not isinstance(key, str) or key.startswith("_"):
                    continue
                try:
                    value = getattr(component, key)
                except Exception:
                    continue
                if _should_include(key, value):
                    flattened[key] = _maybe_redact(key, value)
    return flattened
