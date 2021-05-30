import functools as ft
import asyncio


def _coro(f):
    """
    Run coroutines ad-hoc.

    This is a pretty resource-intensive operation, and it's really only
    used for the CLI application where a single coroutine will get run.
    Don't do this in a production setting, because it's icky. :)

    "Why not asyncio.run?"
    Because that'll close the loop before we stop the connection over to
    the darkseer database, resulting in a messy fit of errors. We'll use
    loop.stop instead.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    @ft.wraps(f)
    def wrapper(*a, **kw):
        try:
            return loop.run_until_complete(f(*a, **kw))
        finally:
            loop.stop()

    return wrapper
