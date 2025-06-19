"""
Root-level pytest configuration for the qdrant-loader workspace.

This conftest.py coordinates test configurations across all packages and test types,
allowing tests to be run from the project root without conflicts.
"""

import glob
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# Project root setup
PROJECT_ROOT = Path(__file__).parent

# Add all package source directories to Python path
PACKAGE_PATHS = [
    PROJECT_ROOT / "packages" / "qdrant-loader" / "src",
    PROJECT_ROOT / "packages" / "qdrant-loader-mcp-server" / "src",
    PROJECT_ROOT / "website",
    PROJECT_ROOT / "website" / "assets",
]

for path in PACKAGE_PATHS:
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))


def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    # Add custom markers
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line(
        "markers", "requires_deps: mark test as requiring optional dependencies"
    )
    config.addinivalue_line(
        "markers", "workflow: marks tests that validate GitHub Actions workflow"
    )

    # Add warning filters
    config.addinivalue_line("filterwarnings", "ignore::DeprecationWarning")
    config.addinivalue_line("filterwarnings", "ignore::PendingDeprecationWarning")
    config.addinivalue_line("filterwarnings", "ignore::bs4.XMLParsedAsHTMLWarning")

    # Set asyncio mode for async tests
    if hasattr(config.option, "asyncio_mode"):
        config.option.asyncio_mode = "strict"


def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle different test types."""
    for item in items:
        # Auto-mark integration tests
        if "integration" in str(item.fspath) or "integration" in item.name:
            item.add_marker(pytest.mark.integration)

        # Auto-mark unit tests
        if "unit" in str(item.fspath) or "unit" in item.name:
            item.add_marker(pytest.mark.unit)

        # Auto-mark slow tests
        if "slow" in item.name or any(
            mark.name == "slow" for mark in item.iter_markers()
        ):
            item.add_marker(pytest.mark.slow)


@pytest.fixture(scope="session")
def project_root():
    """Get the project root directory."""
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def workspace_root():
    """Alias for project_root for backward compatibility."""
    return PROJECT_ROOT


# Website-specific fixtures
@pytest.fixture(scope="session", autouse=True)
def cleanup_test_artifacts():
    """Clean up test artifacts before and after test session."""
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
            for path in glob.glob(str(PROJECT_ROOT / pattern)):
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
def clean_workspace(project_root):
    """Clean workspace fixture that restores working directory and cleans up artifacts."""
    # Store the original working directory before any test changes
    try:
        original_cwd = os.getcwd()
    except (OSError, FileNotFoundError):
        # If current directory doesn't exist, use project root
        original_cwd = str(project_root)

    yield

    # Restore working directory
    try:
        os.chdir(original_cwd)
    except (OSError, FileNotFoundError):
        # If original directory doesn't exist, go to project root
        os.chdir(str(project_root))

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
        for path in glob.glob(str(project_root / pattern)):
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
    return PROJECT_ROOT


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

    privacy_policy_template = """<section class="py-5">
    <div class="container">
        <div class="row justify-content-center">
            <div class="col-lg-10">
                <h1 class="display-5 fw-bold text-primary mb-4">
                    <i class="bi bi-shield-check me-3"></i>Privacy Policy
                </h1>
                <p class="lead text-muted mb-5">
                    Your privacy is important to us.
                </p>
            </div>
        </div>
    </div>
</section>"""

    coverage_template = """<div class="coverage">
    <h1>Coverage Report</h1>
    <p>Test coverage information</p>
</div>"""

    robots_template = """User-agent: *
Allow: /
Sitemap: https://qdrant-loader.net/sitemap.xml"""

    # Write templates
    templates_dir = temp_workspace / "website" / "templates"
    (templates_dir / "base.html").write_text(base_template)
    (templates_dir / "index.html").write_text(index_template)
    (templates_dir / "docs-index.html").write_text(docs_template)
    (templates_dir / "privacy-policy.html").write_text(privacy_policy_template)
    (templates_dir / "coverage-index.html").write_text(coverage_template)
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
    """Create sample coverage data for testing."""
    coverage_dir = tmp_path / "coverage-artifacts"
    coverage_dir.mkdir()

    # Create htmlcov-loader directory
    loader_dir = coverage_dir / "htmlcov-loader"
    loader_dir.mkdir()

    # Create status.json
    status_data = {
        "meta": {
            "version": "7.3.2",
            "timestamp": "2024-01-01T12:00:00",
            "branch_coverage": True,
            "show_contexts": False,
        },
        "totals": {
            "covered_lines": 1500,
            "num_statements": 2000,
            "percent_covered": 75.0,
            "missing_lines": 500,
            "excluded_lines": 0,
        },
    }

    import json

    (loader_dir / "status.json").write_text(json.dumps(status_data, indent=2))

    return coverage_dir


@pytest.fixture
def sample_test_results(temp_workspace):
    """Create sample test results for testing."""
    test_results_dir = temp_workspace / "test-results"
    test_results_dir.mkdir(exist_ok=True)

    # Create status.json
    status_data = {
        "tests": {"total": 150, "passed": 145, "failed": 3, "skipped": 2},
        "coverage": {"line_rate": 0.85, "branch_rate": 0.78},
    }

    import json

    (test_results_dir / "status.json").write_text(json.dumps(status_data, indent=2))

    return test_results_dir
