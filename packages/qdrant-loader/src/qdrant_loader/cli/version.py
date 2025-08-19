from __future__ import annotations


def get_version_str() -> str:
    """Return package version string or 'unknown' if unavailable."""
    try:
        from importlib.metadata import version

        return version("qdrant-loader")
    except Exception:
        return "unknown"


