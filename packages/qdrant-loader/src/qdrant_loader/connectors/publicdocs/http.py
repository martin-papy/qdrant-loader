from __future__ import annotations

import asyncio


async def read_text_response(response) -> str:
    """Raise for status and return response text, guarding mocked double-await."""
    response.raise_for_status()
    text = await response.text()
    if asyncio.iscoroutine(text):  # guard for misconfigured mocks in tests
        text = await text
    return text


async def get_text(session, url: str) -> str:
    response = await session.get(url)
    return await read_text_response(response)


