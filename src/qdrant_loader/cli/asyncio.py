"""
Re-export asyncio functions to make them mockable in tests.
This module provides a simplified interface to asyncio functionality
that can be easily mocked in tests.
"""
from asyncio import (
    run,
    get_event_loop,
    new_event_loop,
    set_event_loop,
)

__all__ = ['run', 'get_event_loop', 'new_event_loop', 'set_event_loop'] 