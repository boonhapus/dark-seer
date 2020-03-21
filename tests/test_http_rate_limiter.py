import time
import asyncio

from ward import test, each

from darkseer.http import AsyncRateLimiter


@test('{limiter} makes {limiter._max_tokens} requests in {limiter._seconds} seconds', tags=['integration'])
async def _(
    limiter=each(
        AsyncRateLimiter(tokens=5, seconds=5, burst=1),
        AsyncRateLimiter(tokens=3, seconds=3, burst=1),
    )
):
    r = 0
    start = time.monotonic()

    while True:
        async with limiter:
            r += 1

        await asyncio.sleep(0)

        # +0.001s to account for ward/asyncio overhead
        elapsed = (time.monotonic() - start)
        print(elapsed)
        if elapsed >= (limiter._seconds + .01):
            break

    assert r == limiter._max_tokens
