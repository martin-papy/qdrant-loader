"""
Pytest configuration and shared fixtures for website build tests.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import os
import sys
import glob

# Add project paths to sys.path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "website"))
sys.path.insert(0, str(project_root / "website" / "assets"))


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_artifacts():
    """Clean up test artifacts before and after test session."""
    project_root = Path(__file__).parent.parent

    # Patterns for test artifacts that might be created
    cleanup_patterns = [
        "test-site",
        "test-artifacts",
        "test-coverage.xml",
        "coverage-website.xml",
        "htmlcov-website",
        ".coverage*",
        "*.coverage",
        "temp_test_dir",
        "custom-site",
        "custom-templates",
    ]

    def cleanup():
        """Remove test artifacts from project root."""
        for pattern in cleanup_patterns:
            for path in glob.glob(str(project_root / pattern)):
                path_obj = Path(path)
                if path_obj.exists():
                    if path_obj.is_dir():
                        shutil.rmtree(path_obj, ignore_errors=True)
                    else:
                        path_obj.unlink(missing_ok=True)

    # Clean up before tests
    cleanup()

    yield

    # Clean up after tests
    cleanup()


@pytest.fixture
def clean_workspace(project_root_dir):
    """Clean workspace fixture that restores working directory and cleans up artifacts."""
    # Store the original working directory before any test changes
    try:
        original_cwd = os.getcwd()
    except (OSError, FileNotFoundError):
        # If current directory doesn't exist, use project root
        original_cwd = str(project_root_dir)

    yield

    # Restore working directory
    try:
        os.chdir(original_cwd)
    except (OSError, FileNotFoundError):
        # If original directory doesn't exist, go to project root
        os.chdir(str(project_root_dir))

    # Clean up any test artifacts in the project root
    cleanup_patterns = [
        "test-site",
        "test-artifacts",
        "custom-site",
        "custom-templates",
        "site",
        "temp_test_dir",
        "*.coverage",
        ".coverage*",
    ]

    for pattern in cleanup_patterns:
        for path in glob.glob(str(project_root_dir / pattern)):
            path_obj = Path(path)
            if path_obj.exists():
                try:
                    if path_obj.is_dir():
                        shutil.rmtree(path_obj)
                    else:
                        path_obj.unlink()
                except (OSError, PermissionError):
                    # Ignore cleanup errors in tests
                    pass


@pytest.fixture(scope="session")
def project_root_dir():
    """Get the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing."""
    temp_dir = tempfile.mkdtemp()
    workspace = Path(temp_dir)
    yield workspace
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_project_structure(temp_workspace):
    """Create a mock project structure for testing."""
    # Create directory structure
    (temp_workspace / "website" / "templates").mkdir(parents=True)
    (temp_workspace / "website" / "assets" / "logos").mkdir(parents=True)
    (temp_workspace / "docs").mkdir()
    (temp_workspace / "coverage-artifacts").mkdir()
    (temp_workspace / "test-results").mkdir()

    # Create pyproject.toml
    pyproject_content = """[project]
name = "qdrant-loader"
version = "0.4.0"
description = "Vector database toolkit for building searchable knowledge bases"
authors = [{name = "Martin Papy", email = "martin.papy@example.com"}]

[project.optional-dependencies]
docs = [
    "tomli>=2.0.0",
    "markdown>=3.5.0",
    "pygments>=2.15.0",
    "cairosvg>=2.7.0",
    "pillow>=10.0.0"
]
"""
    (temp_workspace / "pyproject.toml").write_text(pyproject_content)

    # Create basic templates
    base_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ page_title }} - QDrant Loader</title>
    <meta name="description" content="{{ page_description }}">
    <link rel="canonical" href="{{ canonical_url }}">
    <meta name="author" content="{{ author }}">
    <meta name="version" content="{{ version }}">
</head>
<body>
    <main>{{ content }}</main>
</body>
</html>"""

    index_template = """<div class="hero">
    <h1>Welcome to QDrant Loader</h1>
    <p>Enterprise-ready vector database toolkit</p>
</div>"""

    docs_template = """<div class="docs">
    <h1>Documentation</h1>
    <p>Comprehensive documentation for QDrant Loader</p>
</div>"""

    coverage_template = """<div class="coverage">
    <h1>Coverage Reports</h1>
    <div id="coverage-summary">
        <div id="loader-coverage">Loading...</div>
        <div id="mcp-coverage">Loading...</div>
    </div>
</div>"""

    sitemap_template = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://martin-papy.github.io/qdrant-loader/</loc>
        <lastmod>{{ build_date }}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>1.0</priority>
    </url>
</urlset>"""

    robots_template = """User-agent: *
Allow: /
Sitemap: https://martin-papy.github.io/qdrant-loader/sitemap.xml"""

    # Write templates
    templates_dir = temp_workspace / "website" / "templates"
    (templates_dir / "base.html").write_text(base_template)
    (templates_dir / "index.html").write_text(index_template)
    (templates_dir / "docs-index.html").write_text(docs_template)
    (templates_dir / "coverage-index.html").write_text(coverage_template)
    (templates_dir / "sitemap.xml").write_text(sitemap_template)
    (templates_dir / "robots.txt").write_text(robots_template)

    # Create sample documentation files
    (temp_workspace / "README.md").write_text(
        """# QDrant Loader

Enterprise-ready vector database toolkit for building searchable knowledge bases.

## Features

- Multi-source data loading
- Vector embeddings
- Search capabilities
"""
    )

    (temp_workspace / "docs" / "installation.md").write_text(
        """# Installation

Install QDrant Loader using pip:

```bash
pip install qdrant-loader
```
"""
    )

    # Create sample assets
    assets_dir = temp_workspace / "website" / "assets"
    (assets_dir / "style.css").write_text("body { font-family: Arial, sans-serif; }")
    (assets_dir / "script.js").write_text("console.log('QDrant Loader loaded');")

    # Create sample SVG logo
    svg_content = """<?xml version="1.0" encoding="UTF-8"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
    <rect width="100" height="100" fill="#667eea"/>
    <text x="50" y="55" text-anchor="middle" fill="white" font-size="20">Q</text>
</svg>"""
    (assets_dir / "logos" / "qdrant-loader-icon.svg").write_text(svg_content)

    return temp_workspace


@pytest.fixture
def sample_coverage_data(tmp_path):
    """Create sample coverage data directory with real fixtures."""
    coverage_dir = tmp_path / "coverage-artifacts"
    coverage_dir.mkdir()

    # Use real coverage fixtures if available
    fixtures_dir = Path(__file__).parent / "fixtures"
    if fixtures_dir.exists():
        # Copy real coverage data - extract htmlcov directories to the root level
        loader_fixture = fixtures_dir / "coverage-loader" / "htmlcov-loader"
        mcp_fixture = fixtures_dir / "coverage-mcp" / "htmlcov-mcp"

        if loader_fixture.exists():
            shutil.copytree(loader_fixture, coverage_dir / "htmlcov-loader")

        if mcp_fixture.exists():
            shutil.copytree(mcp_fixture, coverage_dir / "htmlcov-mcp")
    else:
        # Fallback to mock data if fixtures not available
        loader_dir = coverage_dir / "htmlcov-loader"
        loader_dir.mkdir()
        (loader_dir / "index.html").write_text(
            "<html><body>Coverage Report</body></html>"
        )
        (loader_dir / "status.json").write_text(
            '{"coverage": 85.5, "total_statements": 1000, "covered_statements": 855}'
        )

        mcp_dir = coverage_dir / "htmlcov-mcp"
        mcp_dir.mkdir()
        (mcp_dir / "index.html").write_text(
            "<html><body>MCP Coverage Report</body></html>"
        )
        (mcp_dir / "status.json").write_text(
            '{"coverage": 92.3, "total_statements": 500, "covered_statements": 461}'
        )

    return coverage_dir


@pytest.fixture
def sample_test_results(temp_workspace):
    """Create sample test results for testing."""
    test_results_dir = temp_workspace / "test-results"
    test_results_dir.mkdir(exist_ok=True)  # Ensure parent directory exists

    status_data = {
        "overall_status": "success",
        "timestamp": "2025-01-31T12:00:00Z",
        "packages": {"qdrant-loader": "success", "mcp-server": "success"},
    }

    import json

    (test_results_dir / "status.json").write_text(json.dumps(status_data, indent=2))

    return test_results_dir


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line(
        "markers", "requires_deps: mark test as requiring optional dependencies"
    )
