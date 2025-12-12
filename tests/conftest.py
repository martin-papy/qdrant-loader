"""
Pytest configuration and shared fixtures for website build tests.
"""

import glob
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

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
    # Improved cleanup for Windows - retry with delays
    import time
    for attempt in range(3):
        try:
            shutil.rmtree(temp_dir)
            break
        except (PermissionError, OSError):
            if attempt < 2:
                time.sleep(0.1)
            # Ignore cleanup errors on final attempt
            pass


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
                    Your privacy is important to us. This privacy policy explains how we collect, use, and protect your information.
                </p>

                <div class="card border-0 shadow">
                    <div class="card-body p-5">
                        <h2 class="h4 fw-bold mb-3">Information We Collect</h2>
                        <p class="mb-4">
                            We may collect information you provide directly to us, such as when you contact us or use our services.
                        </p>

                        <h2 class="h4 fw-bold mb-3">How We Use Your Information</h2>
                        <p class="mb-4">
                            We use the information we collect to provide, maintain, and improve our services.
                        </p>

                        <h2 class="h4 fw-bold mb-3">Information Sharing</h2>
                        <p class="mb-4">
                            We do not sell, trade, or otherwise transfer your personal information to third parties.
                        </p>

                        <h2 class="h4 fw-bold mb-3">Contact Us</h2>
                        <p class="mb-0">
                            If you have any questions about this privacy policy, please contact us.
                        </p>

                        <div class="mt-4 text-muted small">
                            <p>Last updated: {{ last_updated }}</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</section>"""

    coverage_template = """<!-- Coverage Header -->
<section class="py-5 bg-light">
    <div class="container">
        <div class="row justify-content-center text-center">
            <div class="col-lg-8">
                <h1 class="display-4 fw-bold text-primary">
                    <i class="bi bi-graph-up me-3"></i>Coverage Reports
                </h1>
                <p class="lead text-muted">
                    Test coverage analysis for QDrant Loader packages
                </p>
            </div>
        </div>
    </div>
</section>

<!-- Coverage Overview -->
<section class="py-5">
    <div class="container">
        <div class="row g-4">
            <!-- QDrant Loader Core Coverage -->
            <div class="col-lg-6">
                <div class="card h-100 border-0 shadow card-hover">
                    <div class="card-header bg-primary text-white">
                        <div class="d-flex align-items-center justify-content-between">
                            <h4 class="mb-0">
                                <i class="bi bi-arrow-repeat me-2"></i>QDrant Loader Core
                            </h4>
                            <span id="loader-status" class="badge bg-light text-dark">
                                <span class="status-indicator status-unknown me-1"></span>
                                Checking...
                            </span>
                        </div>
                    </div>
                    <div class="card-body">
                        <div id="loader-coverage">Loading...</div>
                        <div class="d-grid">
                            <a href="loader/" class="btn btn-primary">
                                <i class="bi bi-arrow-right me-2"></i>View Detailed Report
                            </a>
                        </div>
                    </div>
                </div>
            </div>

            <!-- MCP Server Coverage -->
            <div class="col-lg-6">
                <div class="card h-100 border-0 shadow card-hover">
                    <div class="card-header bg-success text-white">
                        <div class="d-flex align-items-center justify-content-between">
                            <h4 class="mb-0">
                                <i class="bi bi-plug me-2"></i>MCP Server
                            </h4>
                            <span id="mcp-status" class="badge bg-light text-dark">
                                <span class="status-indicator status-unknown me-1"></span>
                                Checking...
                            </span>
                        </div>
                    </div>
                    <div class="card-body">
                        <div id="mcp-coverage">Loading...</div>
                        <div class="d-grid">
                            <a href="mcp/" class="btn btn-success">
                                <i class="bi bi-arrow-right me-2"></i>View Detailed Report
                            </a>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Website Coverage -->
            <div class="col-lg-6">
                <div class="card h-100 border-0 shadow card-hover">
                    <div class="card-header bg-info text-white">
                        <div class="d-flex align-items-center justify-content-between">
                            <h4 class="mb-0">
                                <i class="bi bi-globe me-2"></i>Website
                            </h4>
                            <span id="website-status" class="badge bg-light text-dark">
                                <span class="status-indicator status-unknown me-1"></span>
                                Checking...
                            </span>
                        </div>
                    </div>
                    <div class="card-body">
                        <div id="website-coverage">Loading...</div>
                        <div class="d-grid">
                            <a href="website/" class="btn btn-info">
                                <i class="bi bi-arrow-right me-2"></i>View Detailed Report
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</section>

<!-- Test Results Summary -->
<section class="py-5 bg-light">
    <div class="container">
        <div class="row text-center">
            <div class="col-md-4">
                <div class="border rounded p-3">
                    <div class="d-flex align-items-center justify-content-center mb-2">
                        <span id="loader-test-indicator" class="status-indicator status-unknown me-2"></span>
                        <strong>QDrant Loader Tests</strong>
                    </div>
                    <span id="loader-test-status" class="text-muted">Checking...</span>
                </div>
            </div>
            <div class="col-md-4">
                <div class="border rounded p-3">
                    <div class="d-flex align-items-center justify-content-center mb-2">
                        <span id="mcp-test-indicator" class="status-indicator status-unknown me-2"></span>
                        <strong>MCP Server Tests</strong>
                    </div>
                    <span id="mcp-test-status" class="text-muted">Checking...</span>
                </div>
            </div>
            <div class="col-md-4">
                <div class="border rounded p-3">
                    <div class="d-flex align-items-center justify-content-center mb-2">
                        <span id="website-test-indicator" class="status-indicator status-unknown me-2"></span>
                        <strong>Website Tests</strong>
                    </div>
                    <span id="website-test-status" class="text-muted">Checking...</span>
                </div>
            </div>
        </div>
    </div>
</section>

<script>
// Load coverage data for all three packages
fetch('loader/status.json').then(response => response.json()).then(data => {
    document.getElementById('loader-coverage').textContent = 'Loaded';
});

fetch('mcp/status.json').then(response => response.json()).then(data => {
    document.getElementById('mcp-coverage').textContent = 'Loaded';
});

fetch('website/status.json').then(response => response.json()).then(data => {
    document.getElementById('website-coverage').textContent = 'Loaded';
});
</script>"""

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
    """Create sample coverage data directory with mock fixtures."""
    coverage_dir = tmp_path / "coverage-artifacts"
    coverage_dir.mkdir()

    # Always use mock data for predictable testing
    import json

    # Create loader coverage data
    loader_dir = coverage_dir / "htmlcov-loader"
    loader_dir.mkdir()
    (loader_dir / "index.html").write_text(
        "<html><body>Loader Coverage Report</body></html>"
    )
    mock_loader_status = {
        "note": "Mock loader coverage data for testing",
        "format": 5,
        "version": "7.8.2",
        "globals": "mock_hash",
        "files": {
            "mock_loader_file_py": {
                "hash": "mock_hash",
                "index": {
                    "url": "mock_loader_file_py.html",
                    "file": "src/qdrant_loader/mock_file.py",
                    "description": "",
                    "nums": {
                        "precision": 0,
                        "n_files": 1,
                        "n_statements": 100,
                        "n_excluded": 0,
                        "n_missing": 15,
                        "n_branches": 0,
                        "n_partial_branches": 0,
                        "n_missing_branches": 0,
                    },
                },
            }
        },
    }
    (loader_dir / "status.json").write_text(json.dumps(mock_loader_status, indent=2))

    # Create MCP coverage data
    mcp_dir = coverage_dir / "htmlcov-mcp"
    mcp_dir.mkdir()
    (mcp_dir / "index.html").write_text("<html><body>MCP Coverage Report</body></html>")
    mock_mcp_status = {
        "note": "Mock MCP coverage data for testing",
        "format": 5,
        "version": "7.8.2",
        "globals": "mock_hash",
        "files": {
            "mock_mcp_file_py": {
                "hash": "mock_hash",
                "index": {
                    "url": "mock_mcp_file_py.html",
                    "file": "src/mcp_server/mock_file.py",
                    "description": "",
                    "nums": {
                        "precision": 0,
                        "n_files": 1,
                        "n_statements": 50,
                        "n_excluded": 0,
                        "n_missing": 4,
                        "n_branches": 0,
                        "n_partial_branches": 0,
                        "n_missing_branches": 0,
                    },
                },
            }
        },
    }
    (mcp_dir / "status.json").write_text(json.dumps(mock_mcp_status, indent=2))

    # Create website coverage data
    website_dir = coverage_dir / "htmlcov-website"
    website_dir.mkdir()
    (website_dir / "index.html").write_text(
        "<html><body>Website Coverage Report</body></html>"
    )
    mock_website_status = {
        "note": "Mock website coverage data for testing",
        "format": 5,
        "version": "7.8.2",
        "globals": "mock_hash",
        "files": {
            "mock_website_file_py": {
                "hash": "mock_hash",
                "index": {
                    "url": "mock_website_file_py.html",
                    "file": "website/build.py",
                    "description": "",
                    "nums": {
                        "precision": 0,
                        "n_files": 1,
                        "n_statements": 75,
                        "n_excluded": 0,
                        "n_missing": 8,
                        "n_branches": 0,
                        "n_partial_branches": 0,
                        "n_missing_branches": 0,
                    },
                },
            }
        },
    }
    (website_dir / "status.json").write_text(json.dumps(mock_website_status, indent=2))

    return coverage_dir


@pytest.fixture
def sample_test_results(temp_workspace):
    """Create sample test results for testing."""
    test_results_dir = temp_workspace / "test-results"
    test_results_dir.mkdir(exist_ok=True)  # Ensure parent directory exists

    status_data = {
        "overall_status": "success",
        "timestamp": "2025-01-31T12:00:00Z",
        "loader_status": "success",
        "mcp_status": "success",
        "website_status": "success",
        "run_id": "12345",
        "commit_sha": "abc123def456",
        "branch": "main",
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
