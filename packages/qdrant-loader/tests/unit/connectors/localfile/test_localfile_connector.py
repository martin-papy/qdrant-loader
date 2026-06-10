"""Tests for the WS-1 fetch_by_id/list_entity_ids connector contract (LocalFile)."""

import tempfile
from pathlib import Path

import pytest
from pydantic import AnyUrl
from qdrant_loader.config.types import SourceType
from qdrant_loader.connectors.localfile.config import LocalFileConfig
from qdrant_loader.connectors.localfile.connector import LocalFileConnector
from qdrant_loader.core.document import Document


class TestFetchById:
    """Tests for the WS-1 fetch_by_id/list_entity_ids connector contract."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory with test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "test1.txt").write_text("This is test file 1")

            nested = Path(temp_dir) / "subdir" / "test2.md"
            nested.parent.mkdir(exist_ok=True)
            nested.write_text("# Test File 2\nThis is test file 2")

            yield temp_dir

    @pytest.fixture
    def config(self, temp_dir):
        """Create LocalFile configuration."""
        return LocalFileConfig(
            base_url=AnyUrl(f"file://{temp_dir}"),
            source="test-localfile",
            source_type=SourceType.LOCALFILE,
            file_types=["*.txt", "*.md"],
            include_paths=["*"],
            exclude_paths=[],
        )

    @pytest.fixture
    def connector(self, config):
        return LocalFileConnector(config)

    @pytest.mark.asyncio
    async def test_fetch_by_id_returns_document(self, connector):
        """fetch_by_id should return a Document for a top-level file."""
        document = await connector.fetch_by_id("test1.txt")

        assert document is not None
        assert isinstance(document, Document)
        assert document.title == "test1.txt"
        assert document.content == "This is test file 1"

    @pytest.mark.asyncio
    async def test_fetch_by_id_returns_document_for_nested_path(self, connector):
        """fetch_by_id should resolve forward-slash relative paths to nested files."""
        document = await connector.fetch_by_id("subdir/test2.md")

        assert document is not None
        assert document.title == "test2.md"
        assert "Test File 2" in document.content

    @pytest.mark.asyncio
    async def test_fetch_by_id_returns_none_for_nonexistent_file(self, connector):
        """fetch_by_id should return None for a path that does not exist."""
        document = await connector.fetch_by_id("does/not/exist.txt")

        assert document is None

    @pytest.mark.asyncio
    async def test_fetch_by_id_returns_none_for_excluded_file(self, temp_dir):
        """fetch_by_id should return None for a file excluded by file_types."""
        (Path(temp_dir) / "ignored.bin").write_bytes(b"binary-data")

        config = LocalFileConfig(
            base_url=AnyUrl(f"file://{temp_dir}"),
            source="test-localfile",
            source_type=SourceType.LOCALFILE,
            file_types=["*.txt", "*.md"],
            include_paths=["*"],
            exclude_paths=[],
        )
        connector = LocalFileConnector(config)

        document = await connector.fetch_by_id("ignored.bin")

        assert document is None

    @pytest.mark.asyncio
    async def test_list_entity_ids(self, connector):
        """list_entity_ids should yield forward-slash relative paths for processable files."""
        entity_ids = sorted(
            [entity_id async for entity_id in connector.list_entity_ids()]
        )

        assert entity_ids == ["subdir/test2.md", "test1.txt"]

    @pytest.mark.asyncio
    async def test_list_entity_ids_excludes_filtered_files(self, temp_dir):
        """list_entity_ids should not yield files excluded by file_types."""
        (Path(temp_dir) / "ignored.bin").write_bytes(b"binary-data")

        config = LocalFileConfig(
            base_url=AnyUrl(f"file://{temp_dir}"),
            source="test-localfile",
            source_type=SourceType.LOCALFILE,
            file_types=["*.txt", "*.md"],
            include_paths=["*"],
            exclude_paths=[],
        )
        connector = LocalFileConnector(config)

        entity_ids = sorted(
            [entity_id async for entity_id in connector.list_entity_ids()]
        )

        assert entity_ids == ["subdir/test2.md", "test1.txt"]
        assert "ignored.bin" not in entity_ids
