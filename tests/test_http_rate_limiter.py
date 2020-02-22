import time

from ward import test

from dota_info_wrapper.http import AsyncRateLimiter

from tests.common import async_test


@test('AsyncRateLimiter makes {n} requests in {s} seconds')
@async_test
async def _(cls=AsyncRateLimiter, n=3, s=3):
    r = 0
    limiter = cls(tokens=n, seconds=s)
    start = time.monotonic()

    while True:
        print(r)
        async with limiter:
            r += 1

        if (time.monotonic() - start) >= s:
            break

    assert r == n
