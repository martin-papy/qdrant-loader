"""Tests for the main __init__.py module."""

import pytest
from unittest.mock import patch


class TestVersionHandling:
    """Test version handling and lazy imports."""

    def test_version_import_success(self):
        """Test successful version import."""
        import qdrant_loader
        # Should have a version string (either from metadata or fallback)
        assert hasattr(qdrant_loader, '__version__')
        assert isinstance(qdrant_loader.__version__, str)

    def test_version_import_fallback(self):
        """Patch importlib.metadata.version to raise ImportError and verify module fallback."""
        import importlib
        import sys

        # Ensure fresh import under the patched environment
        sys.modules.pop('qdrant_loader', None)

        with patch('importlib.metadata.version', side_effect=ImportError("simulated ImportError")):
            qdrant_loader = importlib.import_module('qdrant_loader')
            assert getattr(qdrant_loader, '__version__') == "unknown"



    @pytest.mark.parametrize(
        "attr_name, expected_path",
        [
            ("ChunkingConfig", "qdrant_loader.config:ChunkingConfig"),
            ("GlobalConfig", "qdrant_loader.config:GlobalConfig"),
            ("SemanticAnalysisConfig", "qdrant_loader.config:SemanticAnalysisConfig"),
            ("Settings", "qdrant_loader.config:Settings"),
            ("Document", "qdrant_loader.core:Document"),
            ("EmbeddingService", "qdrant_loader.core.embedding:EmbeddingService"),
            ("QdrantManager", "qdrant_loader.core.qdrant_manager:QdrantManager"),
        ],
    )
    def test_lazy_imports_resolve_to_expected_symbols(self, attr_name, expected_path):
        """Parameterised verification that lazy-imported attributes resolve to the correct symbols.

        Confirms that each lazily imported attribute is the exact object from its
        defining module and that it is a class or callable (function/class).
        """
        import importlib
        import inspect
        import qdrant_loader

        # Access should trigger lazy import
        resolved_symbol = getattr(qdrant_loader, attr_name)

        module_path, _, symbol_name = expected_path.partition(":")
        expected_module = importlib.import_module(module_path)
        expected_symbol = getattr(expected_module, symbol_name)

        # Identity check: ensure we resolved to the exact exported symbol
        assert (
            resolved_symbol is expected_symbol
        ), f"{attr_name} did not resolve to {expected_path}"

        # Type check: ensure symbol is a class or a function/callable
        assert (
            inspect.isclass(resolved_symbol) or inspect.isfunction(resolved_symbol) or callable(resolved_symbol)
        ), f"{attr_name} is not a class or function"

    def test_lazy_import_invalid_attribute(self):
        """Test lazy import with invalid attribute raises AttributeError."""
        import qdrant_loader
        
        with pytest.raises(AttributeError, match="module 'qdrant_loader' has no attribute 'InvalidAttribute'"):
            _ = qdrant_loader.InvalidAttribute

    def test_all_exports_available(self):
        """Test that all __all__ exports are accessible."""
        import qdrant_loader
        
        for attr_name in qdrant_loader.__all__:
            assert hasattr(qdrant_loader, attr_name), f"Missing export: {attr_name}"
            # Access the attribute to trigger lazy loading
            getattr(qdrant_loader, attr_name)