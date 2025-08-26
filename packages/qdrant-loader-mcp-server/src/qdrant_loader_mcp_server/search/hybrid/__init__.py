"""Hybrid search package with modular subpackages.

Avoid importing implementation modules at package import time to prevent
circular import issues with ``search.components``. Consumers SHOULD import
from concrete submodules, e.g. ``from .engine import HybridSearchEngine``.
"""

__all__: list[str] = []
