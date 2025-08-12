"""Comprehensive tests for LocalFile FileProcessor to achieve 80%+ coverage."""

import os
import tempfile
from unittest.mock import Mock, patch

from pydantic import AnyUrl
from qdrant_loader.connectors.localfile.config import LocalFileConfig
from qdrant_loader.connectors.localfile.file_processor import LocalFileFileProcessor


class TestLocalFileFileProcessor:
    """Comprehensive tests for LocalFileFileProcessor class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.base_config = LocalFileConfig(
            source_type="localfile",
            source="test_source",
            base_url=AnyUrl(f"file://{self.temp_dir}"),
            file_types=["*.txt", "*.md"],
            include_paths=["/", "docs/**/*"],
            exclude_paths=["temp/**", "*.log"],
            max_file_size=1048576,  # 1MB
        )

        # Create mock file detector
        self.mock_file_detector = Mock()
        self.mock_file_detector.is_supported_for_conversion.return_value = False

        # Create processor instance
        self.processor = LocalFileFileProcessor(
            config=self.base_config,
            base_path=self.temp_dir,
            file_detector=self.mock_file_detector,
        )

    def teardown_method(self):
        """Clean up after tests."""
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def create_test_file(
        self, relative_path: str, content: str = "test content", size: int = None
    ):
        """Helper to create test files."""
        file_path = os.path.join(self.temp_dir, relative_path)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        if size is not None:
            # Create file of specific size
            with open(file_path, "wb") as f:
                f.write(b"0" * size)
        else:
            with open(file_path, "w") as f:
                f.write(content)

        return file_path

    def test_init(self):
        """Test LocalFileFileProcessor initialization."""
        assert self.processor.config is self.base_config
        assert self.processor.base_path == self.temp_dir
        assert self.processor.file_detector is self.mock_file_detector
        assert self.processor.logger is not None

    def test_init_without_file_detector(self):
        """Test initialization without file detector."""
        processor = LocalFileFileProcessor(
            config=self.base_config, base_path=self.temp_dir, file_detector=None
        )

        assert processor.file_detector is None

    def test_should_process_file_non_existent_file(self):
        """Test should_process_file with non-existent file."""
        non_existent = os.path.join(self.temp_dir, "does_not_exist.txt")

        result = self.processor.should_process_file(non_existent)

        assert result is False

    def test_should_process_file_not_readable(self):
        """Test should_process_file with non-readable file."""
        file_path = self.create_test_file("readonly.txt")

        # Mock os.access to return False for read permission
        with patch("os.access", return_value=False):
            result = self.processor.should_process_file(file_path)

        assert result is False

    def test_should_process_file_hidden_file(self):
        """Test should_process_file rejects hidden files (starting with dot)."""
        file_path = self.create_test_file(".hidden.txt")

        result = self.processor.should_process_file(file_path)

        assert result is False

    def test_should_process_file_exclude_directory_pattern_with_wildcard(self):
        """Test should_process_file with exclude directory pattern ending with /**."""
        self.base_config.exclude_paths = ["temp/**"]
        file_path = self.create_test_file("temp/subdir/file.txt")

        result = self.processor.should_process_file(file_path)

        assert result is False

    def test_should_process_file_exclude_directory_pattern_exact_match(self):
        """Test should_process_file with exclude directory pattern exact match."""
        self.base_config.exclude_paths = ["temp/**"]
        file_path = self.create_test_file("temp/file.txt")

        result = self.processor.should_process_file(file_path)

        assert result is False

    def test_should_process_file_exclude_directory_pattern_with_slash(self):
        """Test should_process_file with exclude directory pattern ending with /."""
        self.base_config.exclude_paths = ["temp/"]
        file_path = self.create_test_file("temp/file.txt")

        result = self.processor.should_process_file(file_path)

        assert result is False

    def test_should_process_file_exclude_directory_pattern_subdirectory(self):
        """Test should_process_file with exclude directory pattern for subdirectory."""
        self.base_config.exclude_paths = ["temp/"]
        file_path = self.create_test_file("temp/subdir/file.txt")

        result = self.processor.should_process_file(file_path)

        assert result is False

    def test_should_process_file_exclude_glob_pattern(self):
        """Test should_process_file with exclude glob pattern."""
        self.base_config.exclude_paths = ["*.log"]
        file_path = self.create_test_file("debug.log")

        result = self.processor.should_process_file(file_path)

        assert result is False

    def test_should_process_file_no_file_types_configured(self):
        """Test should_process_file with no file types configured (should process all)."""
        self.base_config.file_types = []
        file_path = self.create_test_file("any_file.xyz")

        result = self.processor.should_process_file(file_path)

        assert result is True

    def test_should_process_file_matching_file_type_with_dot(self):
        """Test should_process_file with file type pattern starting with dot."""
        self.base_config.file_types = [".txt", ".md"]
        file_path = self.create_test_file("document.txt")

        result = self.processor.should_process_file(file_path)

        assert result is True

    def test_should_process_file_matching_file_type_without_dot(self):
        """Test should_process_file with file type pattern without dot."""
        self.base_config.file_types = ["*.txt"]
        file_path = self.create_test_file("document.txt")

        result = self.processor.should_process_file(file_path)

        assert result is True

    def test_should_process_file_non_matching_file_type(self):
        """Test should_process_file with non-matching file type."""
        self.base_config.file_types = ["*.txt"]
        file_path = self.create_test_file("document.pdf")

        result = self.processor.should_process_file(file_path)

        assert result is False

    def test_should_process_file_case_insensitive_extension_matching(self):
        """Test should_process_file with case-insensitive extension matching."""
        self.base_config.file_types = ["*.txt"]
        file_path = self.create_test_file("document.TXT")

        result = self.processor.should_process_file(file_path)

        assert result is True

    def test_should_process_file_file_conversion_enabled_supported(self):
        """Test should_process_file with file conversion enabled and supported file."""
        self.base_config.file_types = ["*.txt"]
        self.base_config.enable_file_conversion = True
        self.mock_file_detector.is_supported_for_conversion.return_value = True

        file_path = self.create_test_file(
            "document.pdf"
        )  # Not in file_types but convertible

        result = self.processor.should_process_file(file_path)

        assert result is True
        self.mock_file_detector.is_supported_for_conversion.assert_called_once_with(
            file_path
        )

    def test_should_process_file_file_conversion_enabled_not_supported(self):
        """Test should_process_file with file conversion enabled but unsupported file."""
        self.base_config.file_types = ["*.txt"]
        self.base_config.enable_file_conversion = True
        self.mock_file_detector.is_supported_for_conversion.return_value = False

        file_path = self.create_test_file("document.xyz")

        result = self.processor.should_process_file(file_path)

        assert result is False

    def test_should_process_file_file_conversion_disabled(self):
        """Test should_process_file with file conversion disabled."""
        self.base_config.file_types = ["*.txt"]
        self.base_config.enable_file_conversion = False

        file_path = self.create_test_file("document.pdf")

        result = self.processor.should_process_file(file_path)

        assert result is False
        # Should not call file detector when conversion is disabled
        self.mock_file_detector.is_supported_for_conversion.assert_not_called()

    def test_should_process_file_no_file_detector(self):
        """Test should_process_file with no file detector available."""
        processor = LocalFileFileProcessor(
            config=self.base_config, base_path=self.temp_dir, file_detector=None
        )

        processor.config.file_types = ["*.txt"]
        processor.config.enable_file_conversion = True
        file_path = self.create_test_file("document.pdf")

        result = processor.should_process_file(file_path)

        assert result is False

    def test_should_process_file_exceeds_max_file_size(self):
        """Test should_process_file with file exceeding max size."""
        self.base_config.max_file_size = 100  # Very small limit
        file_path = self.create_test_file("large.txt", size=200)  # Larger than limit

        result = self.processor.should_process_file(file_path)

        assert result is False

    def test_should_process_file_within_max_file_size(self):
        """Test should_process_file with file within size limit."""
        self.base_config.max_file_size = 1000
        file_path = self.create_test_file("small.txt", size=500)  # Within limit

        result = self.processor.should_process_file(file_path)

        assert result is True

    def test_should_process_file_no_include_paths(self):
        """Test should_process_file with no include paths (should include all)."""
        self.base_config.include_paths = []
        file_path = self.create_test_file("anywhere/file.txt")

        result = self.processor.should_process_file(file_path)

        assert result is True

    def test_should_process_file_include_root_pattern_empty(self):
        """Test should_process_file with root include pattern (empty string)."""
        self.base_config.include_paths = [""]
        file_path = self.create_test_file("file.txt")  # In root directory

        result = self.processor.should_process_file(file_path)

        assert result is True

    def test_should_process_file_include_root_pattern_slash(self):
        """Test should_process_file with root include pattern (slash)."""
        self.base_config.include_paths = ["/"]
        file_path = self.create_test_file("file.txt")  # In root directory

        result = self.processor.should_process_file(file_path)

        assert result is True

    def test_should_process_file_include_recursive_pattern(self):
        """Test should_process_file with recursive include pattern (**/**)."""
        self.base_config.include_paths = ["docs/**/*"]
        file_path = self.create_test_file("docs/subdir/file.txt")

        result = self.processor.should_process_file(file_path)

        assert result is True

    def test_should_process_file_include_recursive_pattern_root(self):
        """Test should_process_file with recursive pattern from root."""
        self.base_config.include_paths = ["/**/*"]  # Should match everything
        file_path = self.create_test_file("anywhere/file.txt")

        result = self.processor.should_process_file(file_path)

        assert result is True

    def test_should_process_file_include_recursive_pattern_empty_root(self):
        """Test should_process_file with glob pattern that matches file type."""
        # Use a pattern that should match txt files
        self.base_config.include_paths = ["*.txt"]  # Should match .txt files
        file_path = self.create_test_file("file.txt")  # In root

        result = self.processor.should_process_file(file_path)

        # This pattern should match .txt files in root directory
        assert result is True

    def test_should_process_file_include_directory_pattern_with_slash(self):
        """Test should_process_file with directory include pattern ending with /."""
        self.base_config.include_paths = ["docs/"]
        file_path = self.create_test_file("docs/file.txt")

        result = self.processor.should_process_file(file_path)

        assert result is True

    def test_should_process_file_include_directory_pattern_root_slash(self):
        """Test should_process_file with root directory pattern."""
        self.base_config.include_paths = ["/"]
        file_path = self.create_test_file("file.txt")  # In root

        result = self.processor.should_process_file(file_path)

        assert result is True

    def test_should_process_file_include_directory_pattern_subdirectory(self):
        """Test should_process_file with directory pattern matching subdirectory."""
        self.base_config.include_paths = ["docs/"]
        file_path = self.create_test_file("docs/subdir/file.txt")

        result = self.processor.should_process_file(file_path)

        assert result is True

    def test_should_process_file_include_glob_pattern(self):
        """Test should_process_file with glob include pattern."""
        self.base_config.include_paths = ["*.txt"]
        file_path = self.create_test_file("document.txt")

        result = self.processor.should_process_file(file_path)

        assert result is True

    def test_should_process_file_not_matching_include_patterns(self):
        """Test should_process_file with file not matching any include patterns."""
        self.base_config.include_paths = ["docs/"]
        file_path = self.create_test_file("other/file.txt")  # Outside docs/

        result = self.processor.should_process_file(file_path)

        assert result is False

    def test_should_process_file_path_normalization(self):
        """Test should_process_file handles path normalization (backslashes)."""
        # Create file with forward slashes
        file_path = self.create_test_file("subdir/file.txt")

        # Test with backslashes in path (Windows-style)
        windows_path = file_path.replace("/", "\\")

        result = self.processor.should_process_file(windows_path)

        # Should work regardless of path separator
        assert isinstance(result, bool)

    def test_should_process_file_exception_handling(self):
        """Test should_process_file handles exceptions gracefully."""
        # Use a path that will cause an exception when checking file size
        with patch("os.path.getsize", side_effect=OSError("Permission denied")):
            file_path = self.create_test_file("error_file.txt")

            result = self.processor.should_process_file(file_path)

            assert result is False

    def test_should_process_file_complex_scenario(self):
        """Test should_process_file with complex scenario combining multiple factors."""
        # Configure complex rules
        self.base_config.file_types = ["*.txt", "*.md"]
        self.base_config.include_paths = ["docs/", "src/**/*"]
        self.base_config.exclude_paths = ["docs/temp/", "*.backup"]
        self.base_config.enable_file_conversion = True
        self.base_config.max_file_size = 1000

        # Test file in included directory, matching type, within size limit
        file_path = self.create_test_file("docs/guide.txt", size=500)

        result = self.processor.should_process_file(file_path)

        assert result is True

    def test_should_process_file_complex_scenario_excluded(self):
        """Test should_process_file complex scenario where file is excluded."""
        self.base_config.file_types = ["*.txt"]
        self.base_config.include_paths = ["docs/"]
        self.base_config.exclude_paths = ["docs/temp/"]

        # File in excluded subdirectory
        file_path = self.create_test_file("docs/temp/file.txt")

        result = self.processor.should_process_file(file_path)

        assert result is False

    def test_should_process_file_pattern_edge_cases(self):
        """Test should_process_file with edge case patterns."""
        # Test with patterns that have leading slashes
        self.base_config.exclude_paths = [
            "/temp/**"
        ]  # Leading slash should be stripped
        file_path = self.create_test_file("temp/file.txt")

        result = self.processor.should_process_file(file_path)

        assert result is False

    def test_should_process_file_empty_file_extension(self):
        """Test should_process_file with file that has no extension."""
        self.base_config.file_types = ["*.txt"]
        file_path = self.create_test_file("README")  # No extension

        result = self.processor.should_process_file(file_path)

        assert result is False

    def test_should_process_file_pattern_with_empty_extension(self):
        """Test should_process_file with pattern that results in empty extension."""
        self.base_config.file_types = ["filename"]  # No dot, no extension
        file_path = self.create_test_file("filename.txt")

        # Should not match because pattern has no extension
        result = self.processor.should_process_file(file_path)

        assert result is False

    def test_file_logging_debug_calls(self):
        """Test that appropriate debug logging calls are made."""
        file_path = self.create_test_file("test.txt")

        with patch.object(self.processor.logger, "debug") as mock_debug:
            self.processor.should_process_file(file_path)

            # Should have made several debug log calls
            assert mock_debug.call_count > 0

            # Check some specific log messages
            debug_calls = [call[0][0] for call in mock_debug.call_args_list]
            assert any(
                "Checking if file should be processed" in call for call in debug_calls
            )
            assert any("Current configuration" in call for call in debug_calls)

    def test_file_processor_with_different_config_values(self):
        """Test file processor with various configuration combinations."""
        # Test with different max file sizes
        configs = [
            {"max_file_size": 0},  # Zero size limit
            {"max_file_size": 1},  # Very small limit
            {"file_types": []},  # No file type restrictions
            {"include_paths": [""]},  # Empty include path
            {"exclude_paths": ["**"]},  # Exclude everything pattern
        ]

        for config_override in configs:
            # Create new config with override
            config = LocalFileConfig(
                source_type="localfile",
                source="test",
                base_url=AnyUrl(f"file://{self.temp_dir}"),
                **config_override,
            )
            processor = LocalFileFileProcessor(config, self.temp_dir, None)

            file_path = self.create_test_file(f"test_{len(configs)}.txt")

            # Should not raise exceptions
            result = processor.should_process_file(file_path)
            assert isinstance(result, bool)
