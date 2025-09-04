from __future__ import annotations


def get_version_str() -> str:
    """Return package version string or 'unknown' if the package is not installed.

    Prefer stdlib importlib.metadata; fallback to importlib_metadata for older Python.
    Handle only PackageNotFoundError to avoid silencing unrelated errors.
    """
    try:
        # Prefer the stdlib module when available (Python 3.8+)
        from importlib import metadata as _metadata  # type: ignore[no-redef]
    except ImportError:  # pragma: no cover - fallback path for older Python
        import importlib_metadata as _metadata  # type: ignore[no-redef]

    try:
        return _metadata.version("qdrant-loader")
    except _metadata.PackageNotFoundError:
        return "unknown"
