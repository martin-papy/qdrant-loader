"""Test document ID consistency for LocalFile connector."""

import os
import sys
import tempfile
from pathlib import Path

import pytest
from pydantic import AnyUrl
from qdrant_loader.config.types import SourceType
from qdrant_loader.connectors.localfile import LocalFileConnector
from qdrant_loader.connectors.localfile.config import LocalFileConfig


class TestLocalFileIdConsistency:
    """Test document ID consistency for LocalFile connector."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory with test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            test_file1 = Path(temp_dir) / "test1.txt"
            test_file1.write_text("This is test file 1")

            test_file2 = Path(temp_dir) / "subdir" / "test2.md"
            test_file2.parent.mkdir(exist_ok=True)
            test_file2.write_text("# Test File 2\nThis is test file 2")

            yield temp_dir

    @pytest.fixture
    def localfile_config(self, temp_dir):
        """Create LocalFile configuration."""
        return LocalFileConfig(
            base_url=AnyUrl(f"file://{temp_dir}"),
            source="test-localfile",
            source_type=SourceType.LOCALFILE,
            file_types=["*.txt", "*.md"],
            include_paths=["*"],
            exclude_paths=[],
        )

    @pytest.mark.asyncio
    async def test_document_id_consistency_across_runs(self, localfile_config):
        """Test that document IDs remain consistent across multiple runs."""
        # First run
        connector1 = LocalFileConnector(localfile_config)
        async with connector1:
            documents1 = await connector1.get_documents()

        # Second run
        connector2 = LocalFileConnector(localfile_config)
        async with connector2:
            documents2 = await connector2.get_documents()

        # Should have same number of documents
        assert len(documents1) == len(documents2)
        assert len(documents1) == 2  # test1.txt and test2.md

        # Sort documents by title for consistent comparison
        docs1_sorted = sorted(documents1, key=lambda d: d.title)
        docs2_sorted = sorted(documents2, key=lambda d: d.title)

        # Document IDs should be identical across runs
        for doc1, doc2 in zip(docs1_sorted, docs2_sorted, strict=False):
            print(f"Doc1 ID: {doc1.id}, URL: {doc1.url}")
            print(f"Doc2 ID: {doc2.id}, URL: {doc2.url}")
            assert doc1.id == doc2.id, f"Document IDs differ: {doc1.id} != {doc2.id}"
            assert (
                doc1.url == doc2.url
            ), f"Document URLs differ: {doc1.url} != {doc2.url}"

    @pytest.mark.asyncio
    async def test_document_id_consistency_with_different_working_directories(
        self, localfile_config, temp_dir
    ):
        """Test that document IDs remain consistent when run from different working directories."""
        original_cwd = os.getcwd()

        try:
            # First run from original directory
            connector1 = LocalFileConnector(localfile_config)
            async with connector1:
                documents1 = await connector1.get_documents()

            # Change to a different working directory
            os.chdir(temp_dir)

            # Second run from different directory
            connector2 = LocalFileConnector(localfile_config)
            async with connector2:
                documents2 = await connector2.get_documents()

            # Should have same number of documents
            assert len(documents1) == len(documents2)

            # Sort documents by title for consistent comparison
            docs1_sorted = sorted(documents1, key=lambda d: d.title)
            docs2_sorted = sorted(documents2, key=lambda d: d.title)

            # Document IDs should be identical across runs
            for doc1, doc2 in zip(docs1_sorted, docs2_sorted, strict=False):
                print(f"Doc1 ID: {doc1.id}, URL: {doc1.url}")
                print(f"Doc2 ID: {doc2.id}, URL: {doc2.url}")
                assert (
                    doc1.id == doc2.id
                ), f"Document IDs differ when run from different directories: {doc1.id} != {doc2.id}"
                assert (
                    doc1.url == doc2.url
                ), f"Document URLs differ when run from different directories: {doc1.url} != {doc2.url}"

        finally:
            # Restore original working directory
            os.chdir(original_cwd)

    @pytest.mark.asyncio
    async def test_document_url_format(self, localfile_config, temp_dir):
        """Test that document URLs are properly formatted."""
        connector = LocalFileConnector(localfile_config)
        async with connector:
            documents = await connector.get_documents()

        for doc in documents:
            # URL should start with file://
            assert doc.url.startswith(
                "file://"
            ), f"URL should start with file://: {doc.url}"

            # URL should contain absolute path
            assert os.path.isabs(
                doc.url[7:]
            ), f"URL should contain absolute path: {doc.url}"

            # File should exist at the URL path
            file_path = doc.url[7:]  # Remove file:// prefix
            assert os.path.exists(
                file_path
            ), f"File should exist at URL path: {file_path}"

    @pytest.mark.asyncio
    async def test_document_id_consistency_with_symlinks(self, temp_dir):
        """Test that document IDs remain consistent when accessing files through symlinks."""

        # Create a symlink to the temp directory
        symlink_dir = Path(temp_dir).parent / "symlink_test"
        if symlink_dir.exists():
            symlink_dir.unlink()

        try:
            symlink_dir.symlink_to(temp_dir)
        except OSError as e:
            # Skip test on Windows if user doesn't have symlink privileges
            if sys.platform == "win32" and getattr(e, "winerror", None) == 1314:
                pytest.skip("Symlink creation requires admin privileges on Windows")
            raise
        try:

            # Create test files in the original directory
            test_file = Path(temp_dir) / "test_symlink.txt"
            test_file.write_text("This is a test file for symlink testing")

            print(f"Created test file: {test_file}")
            print(f"File exists: {test_file.exists()}")
            print(f"Symlink dir: {symlink_dir}")
            print(f"Symlink exists: {symlink_dir.exists()}")
            print(f"Symlink file: {symlink_dir / 'test_symlink.txt'}")
            print(f"Symlink file exists: {(symlink_dir / 'test_symlink.txt').exists()}")

            # Create configurations for both paths
            original_config = LocalFileConfig(
                base_url=AnyUrl(f"file://{temp_dir}"),
                source="test-localfile",
                source_type=SourceType.LOCALFILE,
                file_types=["*.txt"],
                include_paths=["*"],
                exclude_paths=[],
            )

            symlink_config = LocalFileConfig(
                base_url=AnyUrl(f"file://{symlink_dir}"),
                source="test-localfile",
                source_type=SourceType.LOCALFILE,
                file_types=["*.txt"],
                include_paths=["*"],
                exclude_paths=[],
            )

            # Get documents from original path
            connector1 = LocalFileConnector(original_config)
            async with connector1:
                documents1 = await connector1.get_documents()

            print(f"Documents from original path: {len(documents1)}")
            for doc in documents1:
                print(f"  - {doc.title}: {doc.url}")

            # Get documents from symlink path
            connector2 = LocalFileConnector(symlink_config)
            async with connector2:
                documents2 = await connector2.get_documents()

            print(f"Documents from symlink path: {len(documents2)}")
            for doc in documents2:
                print(f"  - {doc.title}: {doc.url}")

            # Should have same number of documents
            assert len(documents1) == len(documents2)

            # Find the test file in both document sets
            doc1 = next((d for d in documents1 if d.title == "test_symlink.txt"), None)
            doc2 = next((d for d in documents2 if d.title == "test_symlink.txt"), None)

            assert doc1 is not None, "Document not found in original path"
            assert doc2 is not None, "Document not found in symlink path"

            print(f"Original path doc ID: {doc1.id}, URL: {doc1.url}")
            print(f"Symlink path doc ID: {doc2.id}, URL: {doc2.url}")

            # This is where the issue might manifest - IDs should be the same but URLs might differ
            # The test will fail if os.path.abspath() resolves symlinks differently
            assert (
                doc1.id == doc2.id
            ), f"Document IDs differ for symlink access: {doc1.id} != {doc2.id}"

        finally:
            # Clean up symlink
            if symlink_dir.exists():
                symlink_dir.unlink()

    @pytest.mark.asyncio
    async def test_document_id_consistency_with_path_normalization(self, temp_dir):
        """Test that document IDs remain consistent when using different path representations."""
        # Create test file
        test_file = Path(temp_dir) / "test_relative.txt"
        test_file.write_text("This is a test file for path normalization testing")

        # Create configurations with different path representations
        # Use absolute path
        abs_config = LocalFileConfig(
            base_url=AnyUrl(f"file://{temp_dir}"),
            source="test-localfile",
            source_type=SourceType.LOCALFILE,
            file_types=["*.txt"],
            include_paths=["*"],
            exclude_paths=[],
        )

        # Use path with redundant components (should normalize to same as absolute)
        redundant_path = str(Path(temp_dir) / "." / "subdir" / "..")
        redundant_config = LocalFileConfig(
            base_url=AnyUrl(f"file://{redundant_path}"),
            source="test-localfile",
            source_type=SourceType.LOCALFILE,
            file_types=["*.txt"],
            include_paths=["*"],
            exclude_paths=[],
        )

        # Get documents from absolute path
        connector1 = LocalFileConnector(abs_config)
        async with connector1:
            documents1 = await connector1.get_documents()

        # Get documents from redundant path
        connector2 = LocalFileConnector(redundant_config)
        async with connector2:
            documents2 = await connector2.get_documents()

        # Should have same number of documents
        assert len(documents1) == len(documents2)

        # Find the test file in both document sets
        doc1 = next((d for d in documents1 if d.title == "test_relative.txt"), None)
        doc2 = next((d for d in documents2 if d.title == "test_relative.txt"), None)

        assert doc1 is not None, "Document not found with absolute path"
        assert doc2 is not None, "Document not found with redundant path"

        print(f"Absolute path doc ID: {doc1.id}, URL: {doc1.url}")
        print(f"Redundant path doc ID: {doc2.id}, URL: {doc2.url}")

        # Document IDs should be the same since both paths resolve to the same directory
        assert (
            doc1.id == doc2.id
        ), f"Document IDs differ for different path representations: {doc1.id} != {doc2.id}"
