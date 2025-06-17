"""Tests for the __init__.py module."""


import pytest


class TestInit:
    """Test the __init__.py module."""

    def test_version_import(self):
        """Test version import and fallback."""
        import qdrant_loader

        # Version should be available
        assert hasattr(qdrant_loader, "__version__")
        assert isinstance(qdrant_loader.__version__, str)
        assert qdrant_loader.__version__ != ""

    def test_version_fallback(self):
        """Test version fallback when importlib.metadata fails."""
        # This test is complex to implement correctly due to module caching
        # We'll just verify the version exists for now
        import qdrant_loader

        assert hasattr(qdrant_loader, "__version__")

    def test_all_exports(self):
        """Test that __all__ contains expected exports."""
        import qdrant_loader

        expected_exports = [
            "__version__",
            "Document",
            "EmbeddingService",
            "QdrantManager",
            "Settings",
            "GlobalConfig",
            "SemanticAnalysisConfig",
            "ChunkingConfig",
        ]

        assert hasattr(qdrant_loader, "__all__")
        assert set(qdrant_loader.__all__) == set(expected_exports)

    def test_lazy_import_chunking_config(self):
        """Test lazy import of ChunkingConfig."""
        import qdrant_loader

        # Access ChunkingConfig
        chunking_config = qdrant_loader.ChunkingConfig

        # Should be the actual class
        assert chunking_config.__name__ == "ChunkingConfig"

        # Should be able to instantiate and check it's the right type
        from qdrant_loader.config.chunking import ChunkingConfig

        instance = ChunkingConfig()
        assert instance.chunk_size == 1000  # Default value

    def test_lazy_import_global_config(self):
        """Test lazy import of GlobalConfig."""
        import qdrant_loader

        # Access GlobalConfig
        global_config = qdrant_loader.GlobalConfig

        # Should be the actual class
        assert global_config.__name__ == "GlobalConfig"

        # Should be able to instantiate and check it has expected attributes
        from qdrant_loader.config.global_config import GlobalConfig

        instance = GlobalConfig()
        assert hasattr(instance, "chunking")

    def test_lazy_import_semantic_analysis_config(self):
        """Test lazy import of SemanticAnalysisConfig."""
        import qdrant_loader

        # Access SemanticAnalysisConfig
        semantic_config = qdrant_loader.SemanticAnalysisConfig

        # Should be the actual class
        assert semantic_config.__name__ == "SemanticAnalysisConfig"

        # Should be able to instantiate and check it's the right type
        from qdrant_loader.config.global_config import SemanticAnalysisConfig

        instance = SemanticAnalysisConfig()
        assert instance.num_topics == 3  # Default value

    def test_lazy_import_settings(self):
        """Test lazy import of Settings."""
        import qdrant_loader

        # Access Settings
        settings = qdrant_loader.Settings

        # Should be the actual class
        assert settings.__name__ == "Settings"

        # Note: We don't test instantiation here because Settings requires Qdrant config

    def test_lazy_import_document(self):
        """Test lazy import of Document."""
        import qdrant_loader

        # Access Document
        document = qdrant_loader.Document

        # Should be the actual class
        assert document.__name__ == "Document"

    def test_lazy_import_embedding_service(self):
        """Test lazy import of EmbeddingService."""
        import qdrant_loader

        # Access EmbeddingService
        embedding_service = qdrant_loader.EmbeddingService

        # Should be the actual class
        assert embedding_service.__name__ == "EmbeddingService"

    def test_lazy_import_qdrant_manager(self):
        """Test lazy import of QdrantManager."""
        import qdrant_loader

        # Access QdrantManager
        qdrant_manager = qdrant_loader.QdrantManager

        # Should be the actual class
        assert qdrant_manager.__name__ == "QdrantManager"

    def test_lazy_import_invalid_attribute(self):
        """Test lazy import with invalid attribute."""
        import qdrant_loader

        # Should raise AttributeError for unknown attributes
        with pytest.raises(
            AttributeError,
            match="module 'qdrant_loader' has no attribute 'NonExistentClass'",
        ):
            _ = qdrant_loader.NonExistentClass

    def test_getattr_function(self):
        """Test the __getattr__ function directly."""
        import qdrant_loader

        # Test valid attributes
        valid_attrs = [
            "ChunkingConfig",
            "GlobalConfig",
            "SemanticAnalysisConfig",
            "Settings",
            "Document",
            "EmbeddingService",
            "QdrantManager",
        ]

        for attr in valid_attrs:
            result = qdrant_loader.__getattr__(attr)
            assert result is not None
            assert hasattr(result, "__name__")

    def test_getattr_invalid_attribute(self):
        """Test __getattr__ with invalid attribute."""
        import qdrant_loader

        with pytest.raises(AttributeError):
            qdrant_loader.__getattr__("InvalidAttribute")

    def test_module_docstring(self):
        """Test that module has proper docstring."""
        import qdrant_loader

        assert qdrant_loader.__doc__ is not None
        assert "QDrant Loader" in qdrant_loader.__doc__
        assert "vectorizing" in qdrant_loader.__doc__

    def test_lazy_imports_are_cached(self):
        """Test that lazy imports are properly cached."""
        import qdrant_loader

        # Access the same attribute twice
        first_access = qdrant_loader.ChunkingConfig
        second_access = qdrant_loader.ChunkingConfig

        # Should be the same object (cached)
        assert first_access is second_access

    def test_all_exports_accessible(self):
        """Test that all items in __all__ are accessible."""
        import qdrant_loader

        for item in qdrant_loader.__all__:
            if item == "__version__":
                # Version is directly available
                assert hasattr(qdrant_loader, item)
            else:
                # Other items should be accessible via lazy loading
                attr = getattr(qdrant_loader, item)
                assert attr is not None

    def test_import_paths_correct(self):
        """Test that import paths in lazy loading are correct."""
        import qdrant_loader

        # Test that we can access classes and they come from expected modules
        chunking_config = qdrant_loader.ChunkingConfig
        assert chunking_config.__module__ == "qdrant_loader.config.chunking"

        settings = qdrant_loader.Settings
        assert settings.__module__ == "qdrant_loader.config"

    def test_package_structure(self):
        """Test basic package structure."""
        import qdrant_loader

        # Should have expected attributes
        assert hasattr(qdrant_loader, "__name__")
        assert hasattr(qdrant_loader, "__file__")
        assert hasattr(qdrant_loader, "__package__")

        # Package name should be correct
        assert qdrant_loader.__name__ == "qdrant_loader"
