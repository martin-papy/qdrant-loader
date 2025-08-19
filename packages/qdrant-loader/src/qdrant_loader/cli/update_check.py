from __future__ import annotations


def check_for_updates(version_str: str) -> None:
    """Non-raising check for updates; safe for CLI startup."""
    try:
        from qdrant_loader.utils.version_check import check_version_async

        check_version_async(version_str, silent=False)
    except Exception:
        # Never raise from update checks
        pass


