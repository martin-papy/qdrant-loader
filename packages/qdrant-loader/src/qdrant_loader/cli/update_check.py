from __future__ import annotations


def check_for_updates(version_str: str) -> None:
    """Non-raising check for updates; safe for CLI startup."""
    try:
        import asyncio
        import inspect

        from qdrant_loader.utils.version_check import check_version_async

        result = check_version_async(version_str, silent=False)
        if inspect.isawaitable(result):
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # No running loop: run to completion synchronously
                asyncio.run(result)
            else:
                # Running loop detected: schedule in background to avoid blocking
                try:
                    loop.create_task(result)
                except Exception:
                    # Best effort; never raise from update checks
                    pass
    except Exception:
        # Never raise from update checks
        pass
