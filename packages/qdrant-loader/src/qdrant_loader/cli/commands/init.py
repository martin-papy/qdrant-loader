from __future__ import annotations

from click.exceptions import ClickException


async def run_init(settings, force: bool) -> None:
    try:
        from qdrant_loader.core.init_collection import init_collection
        result = await init_collection(settings, force)
        if not result:
            raise ClickException("Failed to initialize collection")
    except Exception as e:
        raise ClickException(f"Failed to initialize collection: {str(e)!s}") from e


