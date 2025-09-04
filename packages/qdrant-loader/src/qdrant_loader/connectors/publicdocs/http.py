from __future__ import annotations


async def read_text_response(response) -> str:
    """Raise for status and return response text."""
    response.raise_for_status()
    return await response.text()


async def get_text(session, url: str) -> str:
    async with session.get(url) as response:
        return await read_text_response(response)
