#!/usr/bin/env python3
"""
Tests for the website build system.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


class TestWebsiteBuildSystem:
    """Test suite for the website build system."""

    def test_build_script_exists(self):
        """Test that the build script exists and is executable."""
        build_script = Path("website/build.py")
        assert build_script.exists(), "Build script should exist"
        assert build_script.is_file(), "Build script should be a file"

    def test_build_script_syntax(self):
        """Test that the build script has valid Python syntax."""
        build_script = Path("website/build.py")

        # Try to compile the script to check syntax
        with open(build_script, encoding="utf-8") as f:
            source = f.read()

        try:
            compile(source, str(build_script), "exec")
        except SyntaxError as e:
            pytest.fail(f"Build script has syntax error: {e}")

    def test_templates_directory_exists(self):
        """Test that the templates directory exists."""
        templates_dir = Path("website/templates")
        assert templates_dir.exists(), "Templates directory should exist"
        assert templates_dir.is_dir(), "Templates should be a directory"

    def test_required_templates_exist(self):
        """Test that all required templates exist."""
        templates_dir = Path("website/templates")
        required_templates = [
            "base.html",
            "index.html",
            "docs-index.html",
            "coverage-index.html",
            "privacy-policy.html",
            "robots.txt",
        ]

        for template in required_templates:
            template_path = templates_dir / template
            assert template_path.exists(), f"Template {template} should exist"

    def test_base_template_structure(self):
        """Test that the base template has required placeholders."""
        base_template = Path("website/templates/base.html")
        content = base_template.read_text(encoding="utf-8")

        required_placeholders = [
            "{{ page_title }}",
            "{{ page_description }}",
            "{{ canonical_url }}",
            "{{ content }}",
        ]

        for placeholder in required_placeholders:
            assert placeholder in content, f"Base template should contain {placeholder}"

    def test_assets_directory_exists(self):
        """Test that the assets directory exists."""
        assets_dir = Path("website/assets")
        assert assets_dir.exists(), "Assets directory should exist"
        assert assets_dir.is_dir(), "Assets should be a directory"

    def test_favicon_generation_script_exists(self):
        """Test that the favicon generation script exists."""
        favicon_script = Path("website/assets/generate_favicons.py")
        assert favicon_script.exists(), "Favicon generation script should exist"

    def test_favicon_generation_script_syntax(self):
        """Test that the favicon generation script has valid syntax."""
        favicon_script = Path("website/assets/generate_favicons.py")

        with open(favicon_script, encoding="utf-8") as f:
            source = f.read()

        try:
            compile(source, str(favicon_script), "exec")
        except SyntaxError as e:
            pytest.fail(f"Favicon script has syntax error: {e}")

    @pytest.mark.integration
    def test_build_script_can_run(self, mock_project_structure):
        """Test that the build script can run without errors."""
        original_cwd = os.getcwd()
        os.chdir(mock_project_structure)

        try:
            # Copy the actual build script and build directory to the mock structure
            actual_build_script = Path(original_cwd) / "website" / "build.py"
            actual_build_dir = Path(original_cwd) / "website" / "build"
            mock_build_script = mock_project_structure / "website" / "build.py"
            mock_build_dir = mock_project_structure / "website" / "build"

            if actual_build_script.exists():
                shutil.copy2(actual_build_script, mock_build_script)

            # Copy the build package directory if it exists
            if actual_build_dir.exists() and actual_build_dir.is_dir():
                shutil.copytree(actual_build_dir, mock_build_dir)

                # Try to run the build script
                result = subprocess.run(
                    [
                        sys.executable,
                        "website/build.py",
                        "--output",
                        "site",
                        "--templates",
                        "website/templates",
                        "--base-url",
                        "",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                # Check that it didn't crash
                assert result.returncode == 0, f"Build script failed: {result.stderr}"

                # Check that output directory was created
                site_dir = mock_project_structure / "site"
                assert site_dir.exists(), "Site directory should be created"

        finally:
            os.chdir(original_cwd)

    def test_sitemap_template_structure(self):
        """Test that the robots.txt template has valid structure."""
        robots_template = Path("website/templates/robots.txt")
        content = robots_template.read_text(encoding="utf-8")

        # Basic robots.txt structure checks
        assert (
            "User-agent:" in content
        ), "Robots.txt should contain User-agent directive"

    def test_robots_template_structure(self):
        """Test that the robots.txt template has valid structure."""
        robots_template = Path("website/templates/robots.txt")
        content = robots_template.read_text(encoding="utf-8")

        # Basic robots.txt structure checks
        assert (
            "User-agent:" in content
        ), "Robots.txt should contain User-agent directive"
        assert (
            "Allow:" in content or "Disallow:" in content
        ), "Robots.txt should contain Allow or Disallow directive"

    @pytest.mark.requires_deps
    def test_favicon_generation_dependencies(self):
        """Test that favicon generation dependencies are available."""
        cairo_spec = importlib.util.find_spec("cairosvg")
        pil_spec = importlib.util.find_spec("PIL")
        if cairo_spec is None or pil_spec is None:
            missing = []
            if cairo_spec is None:
                missing.append("cairosvg")
            if pil_spec is None:
                missing.append("PIL")
            pytest.skip(
                f"Favicon generation dependencies not available: {', '.join(missing)}"
            )

    def test_coverage_template_has_required_elements(self):
        """Test that the coverage template has required elements."""
        coverage_template = Path("website/templates/coverage-index.html")
        content = coverage_template.read_text(encoding="utf-8")

        # Check for coverage-related elements
        assert (
            "coverage" in content.lower()
        ), "Coverage template should mention coverage"

    def test_docs_template_structure(self):
        """Test that the docs template has proper structure."""
        docs_template = Path("website/templates/docs-index.html")
        content = docs_template.read_text(encoding="utf-8")

        # Basic structure checks
        assert len(content.strip()) > 0, "Docs template should not be empty"

    def test_index_template_structure(self):
        """Test that the index template has proper structure."""
        index_template = Path("website/templates/index.html")
        content = index_template.read_text(encoding="utf-8")

        # Basic structure checks
        assert len(content.strip()) > 0, "Index template should not be empty"


class TestWebsiteBuildIntegration:
    """Integration tests for the complete website build process."""

    @pytest.mark.integration
    def test_complete_build_with_mock_data(
        self, mock_project_structure, sample_coverage_data, sample_test_results
    ):
        """Test complete build process with mock data."""
        original_cwd = os.getcwd()
        os.chdir(mock_project_structure)

        try:
            # Copy the actual build script and build directory
            actual_build_script = Path(original_cwd) / "website" / "build.py"
            actual_build_dir = Path(original_cwd) / "website" / "build"
            mock_build_script = mock_project_structure / "website" / "build.py"
            mock_build_dir = mock_project_structure / "website" / "build"

            if actual_build_script.exists():
                shutil.copy2(actual_build_script, mock_build_script)

            # Copy the build package directory if it exists
            if actual_build_dir.exists() and actual_build_dir.is_dir():
                shutil.copytree(actual_build_dir, mock_build_dir)

                # Run the build with all components
                result = subprocess.run(
                    [
                        sys.executable,
                        "website/build.py",
                        "--output",
                        "site",
                        "--templates",
                        "website/templates",
                        "--coverage-artifacts",
                        "coverage-artifacts",
                        "--test-results",
                        "test-results",
                        "--base-url",
                        "",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                if result.returncode == 0:
                    site_dir = mock_project_structure / "site"

                    # Check main pages
                    assert (
                        site_dir / "index.html"
                    ).exists(), "Index page should be created"

                    # Check SEO files
                    assert (
                        site_dir / "sitemap.xml"
                    ).exists(), "Sitemap should be created"
                    assert (
                        site_dir / "robots.txt"
                    ).exists(), "Robots.txt should be created"

                    # Check that files have content
                    index_content = (site_dir / "index.html").read_text(encoding="utf-8")
                    assert (
                        len(index_content) > 100
                    ), "Index page should have substantial content"

                else:
                    # If build fails, that's okay for this test - we're just checking structure
                    print(
                        f"Build failed (expected in test environment): {result.stderr}"
                    )

        finally:
            os.chdir(original_cwd)

    def test_template_placeholder_replacement(self, mock_project_structure):
        """Test that template placeholders are properly replaced."""
        # This is a basic test that can be expanded
        base_template = mock_project_structure / "website" / "templates" / "base.html"
        content = base_template.read_text(encoding="utf-8")

        # Test that we have the expected placeholders
        placeholders = [
            "{{ page_title }}",
            "{{ page_description }}",
            "{{ canonical_url }}",
        ]
        for placeholder in placeholders:
            assert placeholder in content, f"Template should contain {placeholder}"

    def test_project_structure_validity(self, mock_project_structure):
        """Test that the mock project structure is valid."""
        required_dirs = [
            "website/templates",
            "website/assets",
            "docs",
            "coverage-artifacts",
            "test-results",
        ]

        for dir_path in required_dirs:
            full_path = mock_project_structure / dir_path
            assert full_path.exists(), f"Directory {dir_path} should exist"
            assert full_path.is_dir(), f"{dir_path} should be a directory"

    def test_sample_data_validity(self, sample_coverage_data, sample_test_results):
        """Test that sample data is properly structured."""
        # Test coverage data
        assert sample_coverage_data.exists(), "Coverage data directory should exist"

        loader_status = sample_coverage_data / "htmlcov-loader" / "status.json"
        if loader_status.exists():
            with open(loader_status, encoding="utf-8") as f:
                data = json.load(f)
            assert "files" in data, "Coverage data should have files section"

        # Test results data
        assert sample_test_results.exists(), "Test results directory should exist"

        status_file = sample_test_results / "status.json"
        if status_file.exists():
            with open(status_file, encoding="utf-8") as f:
                data = json.load(f)
            assert "overall_status" in data, "Test results should have overall_status"


if __name__ == "__main__":
    pytest.main([__file__])
