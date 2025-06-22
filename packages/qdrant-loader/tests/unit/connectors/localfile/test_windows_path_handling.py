"""Test Windows path handling for LocalFile connector."""

import pytest
from pydantic import AnyUrl
from qdrant_loader.config.types import SourceType
from qdrant_loader.connectors.localfile import LocalFileConnector
from qdrant_loader.connectors.localfile.config import LocalFileConfig


class TestLocalFileWindowsPathHandling:
    """Test Windows file path handling in LocalFile connector."""

    @pytest.mark.parametrize(
        "input_url,expected_path",
        [
            # Windows drive letter paths
            (
                "file:///C:/Users/test/Documents",
                "C:/Users/test/Documents",
            ),
            (
                "file:///D:/Projects/my-project",
                "D:/Projects/my-project",
            ),
            # Windows paths with spaces
            (
                "file:///C:/Users/test/My%20Documents",
                "C:/Users/test/My Documents",
            ),
            (
                "file:///D:/Program%20Files/MyApp",
                "D:/Program Files/MyApp",
            ),
            # Windows paths with special characters
            (
                "file:///C:/Users/test/Documents%20%26%20Settings",
                "C:/Users/test/Documents & Settings",
            ),
            # Unix paths (should remain unchanged)
            (
                "file:///Users/test/Documents",
                "/Users/test/Documents",
            ),
            (
                "file:///home/user/projects",
                "/home/user/projects",
            ),
            # Unix paths with spaces
            (
                "file:///Users/test/My%20Documents",
                "/Users/test/My Documents",
            ),
            # Edge cases
            (
                "file:///C:",
                "C:",
            ),
            (
                "file:///C:/",
                "C:/",
            ),
        ],
    )
    def test_windows_file_url_parsing(self, input_url: str, expected_path: str):
        """Test that file URLs are parsed correctly for Windows and Unix paths."""
        config = LocalFileConfig(
            base_url=AnyUrl(input_url),
            source="test-source",
            source_type=SourceType.LOCALFILE,
            file_types=["*.txt"],
            include_paths=["*"],
            exclude_paths=[],
        )

        connector = LocalFileConnector(config)
        assert (
            connector.base_path == expected_path
        ), f"Expected {expected_path}, got {connector.base_path}"

    def test_fix_windows_file_path_method(self):
        """Test the _fix_windows_file_path method directly."""
        config = LocalFileConfig(
            base_url=AnyUrl("file:///C:/temp"),
            source="test-source",
            source_type=SourceType.LOCALFILE,
            file_types=["*.txt"],
            include_paths=["*"],
            exclude_paths=[],
        )

        connector = LocalFileConnector(config)

        # Test Windows paths
        assert connector._fix_windows_file_path("/C:/Users/test") == "C:/Users/test"
        assert connector._fix_windows_file_path("/D:/Projects") == "D:/Projects"

        # Test Unix paths (should remain unchanged)
        assert connector._fix_windows_file_path("/Users/test") == "/Users/test"
        assert connector._fix_windows_file_path("/home/user") == "/home/user"

        # Test URL encoded paths
        assert (
            connector._fix_windows_file_path("/C:/Program%20Files")
            == "C:/Program Files"
        )
        assert (
            connector._fix_windows_file_path("/Users/test/My%20Documents")
            == "/Users/test/My Documents"
        )

        # Test edge cases
        assert connector._fix_windows_file_path("/C:") == "C:"
        assert connector._fix_windows_file_path("/") == "/"
        assert connector._fix_windows_file_path("") == ""

    def test_invalid_file_url_scheme(self):
        """Test that non-file URLs are rejected by the config validator."""
        with pytest.raises(
            ValueError, match="base_url for localfile must start with 'file://'"
        ):
            LocalFileConfig(
                base_url=AnyUrl("http://example.com/path"),
                source="test-source",
                source_type=SourceType.LOCALFILE,
                file_types=["*.txt"],
                include_paths=["*"],
                exclude_paths=[],
            )

    @pytest.mark.parametrize(
        "input_url",
        [
            "file:///C:/Users/test/../Documents",
            "file:///C:/Users/test/./Documents",
            "file:///C:/Users/test//Documents",
        ],
    )
    def test_path_normalization_still_works(self, input_url: str):
        """Test that path normalization edge cases don't break the Windows fix."""
        config = LocalFileConfig(
            base_url=AnyUrl(input_url),
            source="test-source",
            source_type=SourceType.LOCALFILE,
            file_types=["*.txt"],
            include_paths=["*"],
            exclude_paths=[],
        )

        connector = LocalFileConnector(config)
        # Should not start with a slash for Windows paths
        assert not connector.base_path.startswith("/C:")
        # Should start with drive letter
        assert connector.base_path.startswith("C:")
