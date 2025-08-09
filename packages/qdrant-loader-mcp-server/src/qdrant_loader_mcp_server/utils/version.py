"""Version utilities for the MCP server."""

from pathlib import Path

import tomli


def get_version() -> str:
    """Get version from pyproject.toml."""
    try:
        # Try to find pyproject.toml in the package directory or parent directories
        current_dir = Path(__file__).parent
        for _ in range(5):  # Look up to 5 levels up
            pyproject_path = current_dir / "pyproject.toml"
            if pyproject_path.exists():
                with open(pyproject_path, "rb") as f:
                    pyproject = tomli.load(f)
                    return pyproject["project"]["version"]
            current_dir = current_dir.parent

        # If not found, try the workspace root
        workspace_root = Path.cwd()
        for package_dir in ["packages/qdrant-loader-mcp-server", "."]:
            pyproject_path = workspace_root / package_dir / "pyproject.toml"
            if pyproject_path.exists():
                with open(pyproject_path, "rb") as f:
                    pyproject = tomli.load(f)
                    return pyproject["project"]["version"]
    except Exception:
        pass
    return "Unknown"
