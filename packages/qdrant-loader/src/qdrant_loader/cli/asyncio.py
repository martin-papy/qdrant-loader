"""
Re-export asyncio functions to make them mockable in tests.
This module provides a simplified interface to asyncio functionality
that can be easily mocked in tests.
"""

import asyncio
from asyncio import (
    get_event_loop,
    new_event_loop,
    run,
    set_event_loop,
)
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any

__all__ = ["run", "get_event_loop", "new_event_loop", "set_event_loop"]

"""Async utilities for the CLI module."""


def async_command(f: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Any]:
    """Decorator to run async commands in the CLI.

    This decorator handles the async event loop properly, ensuring that:
    1. We don't try to create a new event loop if one already exists
    2. We properly clean up the event loop if we create one
    3. We handle both testing and production environments correctly
    """

    @wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running event loop, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            should_close = True
        else:
            should_close = False

        try:
            return loop.run_until_complete(f(*args, **kwargs))
        finally:
            if should_close:
                loop.close()

    return wrapper
