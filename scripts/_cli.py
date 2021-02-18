import functools as ft
import asyncio


_loop = asyncio.get_event_loop()


def coro(f):
    """
    Converts an async command into a sync one.
    """
    @ft.wraps(f)
    def wrapper(*a, **kw):
        return _loop.run_until_complete(f(*a, **kw))

    return wrapper
