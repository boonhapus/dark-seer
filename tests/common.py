import functools as ft
import asyncio


def async_test(fn):
    @ft.wraps(fn)
    def _async_wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        coro = fn(*args, **kwargs)
        return loop.run_until_complete(coro)

    return _async_wrapper


if __name__ == '__main__':
    @async_test
    async def test():
        return 1

    print(test())
