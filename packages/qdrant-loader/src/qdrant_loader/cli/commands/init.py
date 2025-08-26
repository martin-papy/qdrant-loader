from __future__ import annotations

from click.exceptions import ClickException


async def run_init(settings, force: bool) -> None:
    from qdrant_loader.core.init_collection import init_collection

    try:
        result = await init_collection(settings, force)
    except ClickException:
        raise
    except Exception as e:
        raise ClickException(f"Failed to initialize collection: {e}") from e
    if result is False:
        raise ClickException("Failed to initialize collection")
