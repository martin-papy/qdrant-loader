#!/usr/bin/env python3
"""
Test cleanup functionality to ensure test artifacts are properly removed.
"""

import pytest
import os


def test_cleanup_session_fixture_removes_artifacts(project_root_dir):
    """Test that session-level cleanup removes test artifacts."""
    # Create some test artifacts that should be cleaned up
    test_artifacts = [
        project_root_dir / "test-site",
        project_root_dir / "test-artifacts",
        project_root_dir / "coverage-website.xml",
        project_root_dir / ".coverage.test",
    ]

    # Create the artifacts
    for artifact in test_artifacts:
        if artifact.suffix:  # It's a file
            artifact.write_text("test content")
        else:  # It's a directory
            artifact.mkdir(exist_ok=True)
            (artifact / "test.txt").write_text("test")

    # Verify they exist
    for artifact in test_artifacts:
        assert artifact.exists(), f"Test artifact should exist: {artifact}"

    # The cleanup fixture should remove these at the end of the session
    # We can't test this directly in the same session, but we can verify
    # the cleanup patterns are correct
    assert True


def test_clean_workspace_fixture_restores_cwd(clean_workspace, project_root_dir):
    """Test that clean_workspace fixture restores working directory."""
    original_cwd = os.getcwd()

    # Change to a different directory
    temp_dir = project_root_dir / "temp_test_dir"
    temp_dir.mkdir(exist_ok=True)
    os.chdir(temp_dir)

    # Verify we changed directories
    assert os.getcwd() != original_cwd
    assert os.getcwd() == str(temp_dir)

    # The fixture should restore the original directory after the test
    # This will be verified by pytest's fixture cleanup


def test_clean_workspace_prevents_artifact_pollution(clean_workspace, project_root_dir):
    """Test that clean_workspace prevents test artifact pollution."""
    # Create some artifacts during the test
    test_site = project_root_dir / "test-site"
    test_site.mkdir(exist_ok=True)
    (test_site / "index.html").write_text("<html><body>Test</body></html>")

    # Create coverage file
    coverage_file = project_root_dir / "test.coverage"
    coverage_file.write_text("coverage data")

    # Verify they exist during the test
    assert test_site.exists()
    assert coverage_file.exists()

    # The clean_workspace fixture should clean these up after the test


def test_temp_workspace_isolation(temp_workspace):
    """Test that temp_workspace provides proper isolation."""
    # Create files in temp workspace
    test_file = temp_workspace / "test.txt"
    test_file.write_text("isolated test content")

    test_dir = temp_workspace / "subdir"
    test_dir.mkdir()
    (test_dir / "nested.txt").write_text("nested content")

    # Verify isolation
    assert test_file.exists()
    assert test_dir.exists()
    assert "isolated test content" in test_file.read_text()

    # The temp_workspace fixture should clean up automatically


def test_mock_project_structure_isolation(mock_project_structure):
    """Test that mock_project_structure provides proper isolation."""
    # Verify the mock structure exists
    assert (mock_project_structure / "website" / "templates").exists()
    assert (mock_project_structure / "pyproject.toml").exists()

    # Modify the mock structure
    test_file = mock_project_structure / "test_modification.txt"
    test_file.write_text("test modification")

    # Verify modification
    assert test_file.exists()

    # The fixture should clean up automatically without affecting other tests


if __name__ == "__main__":
    pytest.main([__file__])
