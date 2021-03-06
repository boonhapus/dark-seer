import time

from ward import test, each

from darkseer.http import AsyncRateLimiter


@test('{limiter} makes {limiter._max_tokens} requests in {limiter._seconds} seconds', tags=['integration'])
async def _(
    limiter=each(
        AsyncRateLimiter(tokens=1, seconds=1),
        AsyncRateLimiter(tokens=7, seconds=0.33),
    )
):
    r = 0
    start = time.monotonic()

    while True:
        async with limiter:
            r += 1

        # incl. small buffer of .001 to account for asyncio measurements
        if (time.monotonic() - start + .001) >= limiter._seconds:
            break

    assert r == limiter._max_tokens
