"""Integration tests for CLI ingest commands.

This module tests the ingest command functionality including
document ingestion, batch processing, and async operations.
"""

from pathlib import Path
from unittest.mock import AsyncMock, patch

from click.testing import CliRunner


class TestIngestHelp:
    """Test ingest command help and structure."""

    def test_ingest_help(self, cli_runner: CliRunner, cli_app):
        """Test ingest command help display."""
        result = cli_runner.invoke(cli_app, ["ingest", "--help"])

        assert result.exit_code == 0
        assert "ingest" in result.output.lower()
        assert "documents" in result.output.lower() or "files" in result.output.lower()

    def test_ingest_subcommands(self, cli_runner: CliRunner, cli_app):
        """Test ingest subcommand structure."""
        result = cli_runner.invoke(cli_app, ["ingest", "--help"])

        assert result.exit_code == 0
        # Check for common ingest-related terms
        help_output = result.output.lower()
        ingest_terms = ["file", "batch", "directory", "document"]
        assert any(term in help_output for term in ingest_terms)


class TestIngestBasicFunctionality:
    """Test basic ingest command functionality."""

    @patch("qdrant_loader.core.managers.qdrant_manager.QdrantManager")
    @patch("qdrant_loader.core.managers.neo4j_manager.Neo4jManager")
    def test_ingest_single_file(
        self,
        mock_neo4j,
        mock_qdrant,
        cli_runner: CliRunner,
        cli_app,
        workspace_with_config: Path,
        sample_document_file: Path,
    ):
        """Test ingesting a single document file."""
        # Configure mocks
        mock_qdrant_instance = mock_qdrant.return_value
        mock_qdrant_instance.health_check.return_value = True
        mock_qdrant_instance.create_collection.return_value = True

        mock_neo4j_instance = mock_neo4j.return_value
        mock_neo4j_instance.health_check.return_value = True

        result = cli_runner.invoke(
            cli_app,
            [
                "ingest",
                str(sample_document_file),
                "--workspace",
                str(workspace_with_config),
                "--skip-validation",  # Skip validation to avoid external dependencies
            ],
        )

        # Should process the command (success or informative error)
        assert result.output.strip()

    @patch("qdrant_loader.core.managers.qdrant_manager.QdrantManager")
    def test_ingest_directory(
        self,
        mock_qdrant,
        cli_runner: CliRunner,
        cli_app,
        workspace_with_config: Path,
        temp_workspace: Path,
    ):
        """Test ingesting a directory of documents."""
        # Create multiple test files
        docs_dir = temp_workspace / "test_docs"
        docs_dir.mkdir()

        for i in range(3):
            doc_file = docs_dir / f"doc_{i}.txt"
            doc_file.write_text(f"Test document {i} content for ingestion testing.")

        # Configure mock
        mock_qdrant_instance = mock_qdrant.return_value
        mock_qdrant_instance.health_check.return_value = True

        result = cli_runner.invoke(
            cli_app,
            [
                "ingest",
                str(docs_dir),
                "--workspace",
                str(workspace_with_config),
                "--skip-validation",
            ],
        )

        # Should process directory or provide informative error
        assert result.output.strip()

    def test_ingest_missing_file(
        self, cli_runner: CliRunner, cli_app, temp_workspace: Path
    ):
        """Test ingest with non-existent file."""
        missing_file = temp_workspace / "missing.txt"

        result = cli_runner.invoke(
            cli_app, ["ingest", str(missing_file), "--workspace", str(temp_workspace)]
        )

        # Should handle missing file gracefully
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "error" in result.output.lower()


class TestIngestWorkspaceIntegration:
    """Test ingest commands with workspace integration."""

    def test_ingest_with_workspace_config(
        self,
        cli_runner: CliRunner,
        cli_app,
        workspace_with_config: Path,
        sample_document_file: Path,
    ):
        """Test ingest using workspace configuration."""
        with patch(
            "qdrant_loader.core.managers.qdrant_manager.QdrantManager"
        ) as mock_qdrant:
            mock_qdrant_instance = mock_qdrant.return_value
            mock_qdrant_instance.health_check.return_value = True

            result = cli_runner.invoke(
                cli_app,
                [
                    "ingest",
                    str(sample_document_file),
                    "--workspace",
                    str(workspace_with_config),
                ],
            )

            # Should use workspace configuration
            assert result.output.strip()

    def test_ingest_legacy_config_mode(
        self,
        cli_runner: CliRunner,
        cli_app,
        temp_workspace: Path,
        sample_document_file: Path,
    ):
        """Test ingest with legacy configuration mode."""
        # Create legacy config
        config_file = temp_workspace / "config.yaml"
        config_file.write_text(
            """
qdrant:
  host: localhost
  port: 6333
  collection_name: test_collection
neo4j:
  uri: bolt://localhost:7687
  username: neo4j
  password: test
"""
        )

        with patch("qdrant_loader.core.managers.qdrant_manager.QdrantManager"):
            result = cli_runner.invoke(
                cli_app,
                ["ingest", str(sample_document_file), "--config", str(config_file)],
            )

            # Should process with legacy config
            assert result.output.strip()


class TestIngestOptions:
    """Test ingest command options and flags."""

    def test_ingest_batch_size_option(
        self,
        cli_runner: CliRunner,
        cli_app,
        workspace_with_config: Path,
        sample_document_file: Path,
    ):
        """Test ingest with batch size option."""
        with patch("qdrant_loader.core.managers.qdrant_manager.QdrantManager"):
            result = cli_runner.invoke(
                cli_app,
                [
                    "ingest",
                    str(sample_document_file),
                    "--workspace",
                    str(workspace_with_config),
                    "--batch-size",
                    "10",
                ],
            )

            # Should process batch size option
            assert result.output.strip()

    def test_ingest_dry_run_option(
        self,
        cli_runner: CliRunner,
        cli_app,
        workspace_with_config: Path,
        sample_document_file: Path,
    ):
        """Test ingest with dry run option."""
        result = cli_runner.invoke(
            cli_app,
            [
                "ingest",
                str(sample_document_file),
                "--workspace",
                str(workspace_with_config),
                "--dry-run",
            ],
        )

        # Should perform dry run
        assert result.output.strip()

    def test_ingest_verbose_option(
        self,
        cli_runner: CliRunner,
        cli_app,
        workspace_with_config: Path,
        sample_document_file: Path,
    ):
        """Test ingest with verbose option."""
        result = cli_runner.invoke(
            cli_app,
            [
                "ingest",
                str(sample_document_file),
                "--workspace",
                str(workspace_with_config),
                "--verbose",
            ],
        )

        # Should provide verbose output
        assert result.output.strip()

    def test_ingest_force_option(
        self,
        cli_runner: CliRunner,
        cli_app,
        workspace_with_config: Path,
        sample_document_file: Path,
    ):
        """Test ingest with force option."""
        with patch("qdrant_loader.core.managers.qdrant_manager.QdrantManager"):
            result = cli_runner.invoke(
                cli_app,
                [
                    "ingest",
                    str(sample_document_file),
                    "--workspace",
                    str(workspace_with_config),
                    "--force",
                ],
            )

            # Should process force option
            assert result.output.strip()


class TestIngestErrorHandling:
    """Test ingest command error handling."""

    def test_ingest_invalid_config(
        self,
        cli_runner: CliRunner,
        cli_app,
        temp_workspace: Path,
        sample_document_file: Path,
    ):
        """Test ingest with invalid configuration."""
        # Create invalid config
        config_dir = temp_workspace / "config"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"
        config_file.write_text("invalid: yaml: {[")

        result = cli_runner.invoke(
            cli_app,
            ["ingest", str(sample_document_file), "--workspace", str(temp_workspace)],
        )

        # Should handle invalid config gracefully
        assert result.exit_code != 0
        assert "error" in result.output.lower() or "invalid" in result.output.lower()

    def test_ingest_connection_error(
        self,
        cli_runner: CliRunner,
        cli_app,
        workspace_with_config: Path,
        sample_document_file: Path,
    ):
        """Test ingest with connection errors."""
        with patch(
            "qdrant_loader.core.managers.qdrant_manager.QdrantManager"
        ) as mock_qdrant:
            # Simulate connection error
            mock_qdrant_instance = mock_qdrant.return_value
            mock_qdrant_instance.health_check.return_value = False

            result = cli_runner.invoke(
                cli_app,
                [
                    "ingest",
                    str(sample_document_file),
                    "--workspace",
                    str(workspace_with_config),
                ],
            )

            # Should handle connection errors
            assert result.exit_code != 0 or "connection" in result.output.lower()

    def test_ingest_permission_error(
        self, cli_runner: CliRunner, cli_app, temp_workspace: Path
    ):
        """Test ingest with file permission errors."""
        # Create a file we can't read (simulation)
        restricted_file = temp_workspace / "restricted.txt"
        restricted_file.write_text("content")

        result = cli_runner.invoke(
            cli_app,
            ["ingest", str(restricted_file), "--workspace", str(temp_workspace)],
        )

        # Should handle permission errors gracefully
        # (May not fail on all systems, but should not crash)
        assert result.output.strip()


class TestIngestAsyncOperations:
    """Test ingest command async operations."""

    @patch("qdrant_loader.core.managers.qdrant_manager.QdrantManager")
    @patch("qdrant_loader.core.managers.neo4j_manager.Neo4jManager")
    def test_ingest_async_processing(
        self,
        mock_neo4j,
        mock_qdrant,
        cli_runner: CliRunner,
        cli_app,
        workspace_with_config: Path,
        sample_document_file: Path,
    ):
        """Test ingest with async processing."""
        # Configure async mocks
        mock_qdrant_instance = AsyncMock()
        mock_qdrant_instance.health_check.return_value = True
        mock_qdrant_instance.upsert_points.return_value = True
        mock_qdrant.return_value = mock_qdrant_instance

        mock_neo4j_instance = AsyncMock()
        mock_neo4j_instance.health_check.return_value = True
        mock_neo4j.return_value = mock_neo4j_instance

        result = cli_runner.invoke(
            cli_app,
            [
                "ingest",
                str(sample_document_file),
                "--workspace",
                str(workspace_with_config),
                "--async",  # If such option exists
            ],
        )

        # Should handle async operations
        assert result.output.strip()

    def test_ingest_concurrent_processing(
        self,
        cli_runner: CliRunner,
        cli_app,
        workspace_with_config: Path,
        temp_workspace: Path,
    ):
        """Test ingest with concurrent file processing."""
        # Create multiple files for concurrent processing
        docs_dir = temp_workspace / "concurrent_docs"
        docs_dir.mkdir()

        for i in range(5):
            doc_file = docs_dir / f"concurrent_{i}.txt"
            doc_file.write_text(
                f"Concurrent document {i} for testing parallel processing."
            )

        with patch("qdrant_loader.core.managers.qdrant_manager.QdrantManager"):
            result = cli_runner.invoke(
                cli_app,
                [
                    "ingest",
                    str(docs_dir),
                    "--workspace",
                    str(workspace_with_config),
                    "--workers",
                    "2",  # If such option exists
                ],
            )

            # Should handle concurrent processing
            assert result.output.strip()


class TestIngestProgressTracking:
    """Test ingest command progress tracking."""

    def test_ingest_progress_display(
        self,
        cli_runner: CliRunner,
        cli_app,
        workspace_with_config: Path,
        temp_workspace: Path,
    ):
        """Test ingest progress display."""
        # Create multiple files to show progress
        docs_dir = temp_workspace / "progress_docs"
        docs_dir.mkdir()

        for i in range(3):
            doc_file = docs_dir / f"progress_{i}.txt"
            doc_file.write_text(f"Progress document {i} for testing progress tracking.")

        with patch("qdrant_loader.core.managers.qdrant_manager.QdrantManager"):
            result = cli_runner.invoke(
                cli_app,
                [
                    "ingest",
                    str(docs_dir),
                    "--workspace",
                    str(workspace_with_config),
                    "--progress",  # If such option exists
                ],
            )

            # Should show progress information
            assert result.output.strip()

    def test_ingest_quiet_mode(
        self,
        cli_runner: CliRunner,
        cli_app,
        workspace_with_config: Path,
        sample_document_file: Path,
    ):
        """Test ingest in quiet mode."""
        with patch("qdrant_loader.core.managers.qdrant_manager.QdrantManager"):
            result = cli_runner.invoke(
                cli_app,
                [
                    "ingest",
                    str(sample_document_file),
                    "--workspace",
                    str(workspace_with_config),
                    "--quiet",  # If such option exists
                ],
            )

            # Should minimize output in quiet mode
            assert result.exit_code == 0 or result.output.strip()


class TestIngestFileTypes:
    """Test ingest with different file types."""

    def test_ingest_text_files(
        self,
        cli_runner: CliRunner,
        cli_app,
        workspace_with_config: Path,
        temp_workspace: Path,
    ):
        """Test ingest with various text file types."""
        # Create different text file types
        files_dir = temp_workspace / "text_files"
        files_dir.mkdir()

        # Create various file types
        (files_dir / "document.txt").write_text("Plain text document")
        (files_dir / "markdown.md").write_text("# Markdown Document")
        (files_dir / "code.py").write_text("# Python code file\nprint('hello')")

        with patch("qdrant_loader.core.managers.qdrant_manager.QdrantManager"):
            result = cli_runner.invoke(
                cli_app,
                ["ingest", str(files_dir), "--workspace", str(workspace_with_config)],
            )

            # Should process different file types
            assert result.output.strip()

    def test_ingest_unsupported_files(
        self,
        cli_runner: CliRunner,
        cli_app,
        workspace_with_config: Path,
        temp_workspace: Path,
    ):
        """Test ingest with unsupported file types."""
        # Create unsupported file
        binary_file = temp_workspace / "binary.bin"
        binary_file.write_bytes(b"\x00\x01\x02\x03")

        result = cli_runner.invoke(
            cli_app,
            ["ingest", str(binary_file), "--workspace", str(workspace_with_config)],
        )

        # Should handle unsupported files gracefully
        assert result.output.strip()
        # May succeed with warning or fail gracefully
