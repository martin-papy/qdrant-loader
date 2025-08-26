from __future__ import annotations

import asyncio


async def cancel_all_tasks() -> None:
    """Cancel all pending asyncio tasks except the current one and wait for them."""
    tasks = [
        t
        for t in asyncio.all_tasks()
        if t is not asyncio.current_task() and not t.done()
    ]
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
