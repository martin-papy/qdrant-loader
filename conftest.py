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

    # Only add bs4 warning filter if BeautifulSoup4 is available
    try:
        import bs4

        config.addinivalue_line("filterwarnings", "ignore::bs4.XMLParsedAsHTMLWarning")
    except ImportError:
        # bs4 not available, skip the warning filter
        pass

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

    # Use the actual coverage template content with loader-coverage elements
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
                <div id="test-status-banner" class="alert d-none" role="alert">
                    <div class="d-flex align-items-center justify-content-center">
                        <span id="status-indicator" class="status-indicator me-2"></span>
                        <span id="status-text"></span>
                    </div>
                </div>
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
                        <p class="card-text mb-4">
                            Main package coverage including connectors, processing pipeline, and CLI tools.
                        </p>

                        <div class="row text-center mb-4">
                            <div class="col-12">
                                <div class="border rounded p-3" id="loader-coverage">
                                    <h5 class="text-primary mb-1" id="loader-line-coverage">--</h5>
                                    <small class="text-muted">Line Coverage</small>
                                </div>
                            </div>
                        </div>

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
                        <p class="card-text mb-4">
                            Model Context Protocol server implementation and search capabilities.
                        </p>

                        <div class="row text-center mb-4">
                            <div class="col-12">
                                <div class="border rounded p-3" id="mcp-coverage">
                                    <h5 class="text-primary mb-1" id="mcp-line-coverage">--</h5>
                                    <small class="text-muted">Line Coverage</small>
                                </div>
                            </div>
                        </div>

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
                        <p class="card-text mb-4">
                            Website build system, templates, and documentation generation tools.
                        </p>

                        <div class="row text-center mb-4">
                            <div class="col-12">
                                <div class="border rounded p-3" id="website-coverage">
                                    <h5 class="text-primary mb-1" id="website-line-coverage">--</h5>
                                    <small class="text-muted">Line Coverage</small>
                                </div>
                            </div>
                        </div>

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

<!-- Test Information -->
<section class="py-5 bg-light">
    <div class="container">
        <div class="row justify-content-center">
            <div class="col-lg-8">
                <div class="card border-0 shadow">
                    <div class="card-header bg-info text-white">
                        <h4 class="mb-0">
                            <i class="bi bi-info-circle me-2"></i>Test Run Information
                        </h4>
                    </div>
                    <div class="card-body">
                        <div class="row mt-4">
                            <div class="col-12">
                                <h6 class="text-muted">Test Results Summary</h6>
                                <div class="row text-center">
                                    <div class="col-md-4">
                                        <div class="border rounded p-3">
                                            <div class="d-flex align-items-center justify-content-center mb-2">
                                                <span id="loader-test-indicator"
                                                    class="status-indicator status-unknown me-2"></span>
                                                <strong>QDrant Loader Tests</strong>
                                            </div>
                                            <span id="loader-test-status" class="text-muted">Checking...</span>
                                        </div>
                                    </div>
                                    <div class="col-md-4">
                                        <div class="border rounded p-3">
                                            <div class="d-flex align-items-center justify-content-center mb-2">
                                                <span id="mcp-test-indicator"
                                                    class="status-indicator status-unknown me-2"></span>
                                                <strong>MCP Server Tests</strong>
                                            </div>
                                            <span id="mcp-test-status" class="text-muted">Checking...</span>
                                        </div>
                                    </div>
                                    <div class="col-md-4">
                                        <div class="border rounded p-3">
                                            <div class="d-flex align-items-center justify-content-center mb-2">
                                                <span id="website-test-indicator"
                                                    class="status-indicator status-unknown me-2"></span>
                                                <strong>Website Tests</strong>
                                            </div>
                                            <span id="website-test-status" class="text-muted">Checking...</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</section>

<script>
    // Load coverage data for all packages
    Promise.all([
        fetch('loader/status.json').then(response => response.json()).catch(() => null),
        fetch('mcp/status.json').then(response => response.json()).catch(() => null),
        fetch('website/status.json').then(response => response.json()).catch(() => null)
    ]).then(([loaderData, mcpData, websiteData]) => {
        console.log('Coverage data loaded');
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
    """Create sample coverage data for testing."""
    coverage_dir = tmp_path / "coverage-artifacts"
    coverage_dir.mkdir()

    # Create htmlcov-loader directory
    loader_dir = coverage_dir / "htmlcov-loader"
    loader_dir.mkdir()

    # Create status.json with the required "files" key
    status_data = {
        "meta": {
            "version": "7.3.2",
            "timestamp": "2024-01-01T12:00:00",
            "branch_coverage": True,
            "show_contexts": False,
        },
        "files": {
            "mock_file_py": {
                "hash": "mock_hash",
                "index": {
                    "nums": {
                        "precision": 0,
                        "n_files": 1,
                        "n_statements": 100,
                        "n_excluded": 0,
                        "n_missing": 15,
                        "n_branches": 0,
                        "n_partial_branches": 0,
                        "n_missing_branches": 0,
                    }
                },
            }
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

    # Create MCP coverage data
    mcp_dir = coverage_dir / "htmlcov-mcp"
    mcp_dir.mkdir()
    (mcp_dir / "index.html").write_text("<html><body>MCP Coverage Report</body></html>")
    mcp_status_data = {
        "meta": {
            "version": "7.3.2",
            "timestamp": "2024-01-01T12:00:00",
            "branch_coverage": True,
            "show_contexts": False,
        },
        "files": {
            "mock_mcp_file_py": {
                "hash": "mock_hash",
                "index": {
                    "nums": {
                        "precision": 0,
                        "n_files": 1,
                        "n_statements": 50,
                        "n_excluded": 0,
                        "n_missing": 4,
                        "n_branches": 0,
                        "n_partial_branches": 0,
                        "n_missing_branches": 0,
                    }
                },
            }
        },
        "totals": {
            "covered_lines": 46,
            "num_statements": 50,
            "percent_covered": 92.0,
            "missing_lines": 4,
            "excluded_lines": 0,
        },
    }
    (mcp_dir / "status.json").write_text(json.dumps(mcp_status_data, indent=2))

    # Create website coverage data
    website_dir = coverage_dir / "htmlcov-website"
    website_dir.mkdir()
    (website_dir / "index.html").write_text(
        "<html><body>Website Coverage Report</body></html>"
    )
    website_status_data = {
        "meta": {
            "version": "7.3.2",
            "timestamp": "2024-01-01T12:00:00",
            "branch_coverage": True,
            "show_contexts": False,
        },
        "files": {
            "mock_website_file_py": {
                "hash": "mock_hash",
                "index": {
                    "nums": {
                        "precision": 0,
                        "n_files": 1,
                        "n_statements": 75,
                        "n_excluded": 0,
                        "n_missing": 8,
                        "n_branches": 0,
                        "n_partial_branches": 0,
                        "n_missing_branches": 0,
                    }
                },
            }
        },
        "totals": {
            "covered_lines": 67,
            "num_statements": 75,
            "percent_covered": 89.3,
            "missing_lines": 8,
            "excluded_lines": 0,
        },
    }
    (website_dir / "status.json").write_text(json.dumps(website_status_data, indent=2))

    return coverage_dir


@pytest.fixture
def sample_test_results(temp_workspace):
    """Create sample test results for testing."""
    test_results_dir = temp_workspace / "test-results"
    test_results_dir.mkdir(exist_ok=True)

    # Create status.json with the expected "overall_status" key
    status_data = {
        "overall_status": "success",
        "timestamp": "2025-01-31T12:00:00Z",
        "tests": {"total": 150, "passed": 145, "failed": 3, "skipped": 2},
        "coverage": {"line_rate": 0.85, "branch_rate": 0.78},
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
