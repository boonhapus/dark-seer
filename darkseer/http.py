import collections
import asyncio
import time

import httpx

from darkseer import __version__


class AsyncRateLimiter:
    """
    Implementation of the token bucket algorithm.

    Attributes
    ----------
    tokens : int
        number of allowable requests within a period

    seconds : int
        amount of time between period resets

    burst : int, default <tokens>
        number of consecutive requests before limiting happens
    """
    def __init__(self, tokens: int, seconds: int, *, burst: int=None):
        self._max_tokens = tokens
        self._seconds = seconds
        self._burst = burst if burst is not None else tokens
        self._in_queue = {}
        self._last_checked = None
        self.tokens = self._burst

    @property
    def rate(self) -> float:
        return self._max_tokens / self._seconds

    def _flow(self):
        """
        Add tokens to our bucket based on how much time has passed.
        """
        now = time.monotonic()

        if self._last_checked is None:
            self._last_checked = now

        if self.tokens < min(self._burst, self._max_tokens):
            elapsed_s = now - self._last_checked
            new_tokens = elapsed_s * self.rate
            self.tokens = min(self.tokens + new_tokens, self._burst, self._max_tokens)

        self._last_checked = now

    def has_capacity(self) -> bool:
        """
        Check if the bucket has capacity.

        This opportunistically will add tokens into the bucket.
        """
        self._flow()

        if self.tokens < 1:
            return False

        # since we have some tokens, signal to our "next in queue"
        # NOTE: he won't actually wake up until this_task awaits
        try:
            fut = next(f for f in self._in_queue.values() if not f.done())
        except StopIteration:
            pass
        else:
            fut.set_result('ayy boi wakeup')

        return True

    async def acquire(self):
        """
        Acquire a token from our bucket.

        If no tokens are available, block until one becomes available.
        """
        loop = asyncio.get_running_loop()
        this_task = asyncio.current_task()

        while not self.has_capacity():
            self._in_queue[this_task] = fut = loop.create_future()
            try:
                await asyncio.wait_for(fut, timeout=1 / self.rate)
            except asyncio.TimeoutError:
                pass
            finally:
                fut.cancel()
        else:
            self._in_queue.pop(this_task, None)

        self.tokens -= 1

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exception_type, exception, traceback):
        """
        Work is only necessary here if there's something to clean up.

        TODO:
        """
        # cleanup .. ?

    def __repr__(self):
        t = self._max_tokens
        s = self._seconds
        b = self._burst
        return f'AsyncRateLimiter(tokens={t}, seconds={s}, burst={b})'

    def __str__(self):
        return f'<AsyncRateLimiter @ {self.rate:.2f} requests per second>'


class AsyncThrottledClient:
    """
    An HTTP client with a built-in rate limiter.

    Attributes
    ----------
    name : str
        arbitrary name of the HTTP client

    rate_limiter : AsyncRateLimiter, default AsyncRateLimiter(tokens=1, seconds=1)
        limiter to throttle requests with
    """
    def __init__(self, name: str, rate_limiter: AsyncRateLimiter=None, **opts):
        _default_opts = {
            'headers': {
                'user-agent': f'DarkSeerBot/{__version__} (+github: dark-seer)'
            }
        }

        d = collections.defaultdict(dict)
        d.update(_default_opts)
        [d[k].update(nested) for k, nested in opts.items()]

        self.name = name
        self.rate_limiter = rate_limiter
        self._client = httpx.AsyncClient(**dict(d))

    @property
    def rate_limiter(self) -> AsyncRateLimiter:
        return self._rate_limiter

    @rate_limiter.setter
    def rate_limiter(self, limiter):
        if limiter is None:
            limiter = AsyncRateLimiter(tokens=1, seconds=1)

        try:
            limiter.__aenter__
        except AttributeError:
            raise ValueError(
                'limiter must support usage as an async context manager!'
            )

        self._rate_limiter = limiter

    async def aclose(self):
        """
        Simply passthrough the httpx Client.aclose().
        """
        return await self._client.aclose()

    async def _request(self, *args, **kwargs) -> httpx.Response:
        """
        Sends an HTTP request.

        TODO: clean up kwargs
        """
        async with self.rate_limiter:
            # TODO: try/except here to handle HOURLY/MONTHLY rate limits?
            r = await self._client.request(*args, **kwargs)

        return r

    async def get(self, *args, **kwargs) -> httpx.Response:
        """
        Sends a GET request.

        TODO: clean up kwargs
        """
        return await self._request('GET', *args, **kwargs)

    async def post(self, *args, **kwargs) -> httpx.Response:
        """
        Sends a POST request.

        TODO: clean up kwargs
        """
        return await self._request('POST', *args, **kwargs)

    def __str__(self):
        return f'<HTTP client for {self.name}>'
