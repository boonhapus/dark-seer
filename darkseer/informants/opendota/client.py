from typing import Dict, List
import logging
import asyncio

import httpx

from darkseer.util import RateLimitedHTTPClient, FileCache


log = logging.getLogger(__name__)
_cache = FileCache('C:/projects/dark-seer/scripts/cache')


class OpenDota(RateLimitedHTTPClient):
    """
    Wrapper around the OPENDOTA REST API.

    Documentation:
        https://www.opendota.com/api-keys
        https://docs.opendota.com/#section/Introduction

    Rate limit is 50K/month, 60/minute.
    """
    def __init__(self):
        super().__init__(tokens=60, seconds=60, base_url='https://api.opendota.com/api', timeout=None)
        # TODO
        #   if api_key given, raise limit to 1200/minute
        #
        # https://docs.opendota.com/#section/Authentication
        self.month_tokens = 50000

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        if self.tokens < 30 or self.month_tokens < 500:
            log.info(
                f'there are {self.tokens} tokens left this minute and '
                f'{self.month_tokens:,} this month'
            )

        return await super().__aexit__(exc_type, exc_value, traceback)

    #

    @property
    def burst(self) -> float:
        """
        OPENDOTA allows a 60req/min burst.
        """
        return 60 / 60

    async def wait_for_token(self, *, override: float=None) -> None:
        """
        Block the context until a token is available.
        """
        await asyncio.sleep(override or self.burst)

    async def request(self, *a, backoff_: int=0, **kw) -> httpx.Response:
        """
        Make a request, adjusting tokens if necessary.

        Parameters
        ----------
        backoff_ : int, default 0
          linear factor to wait in between retries in case of an error

        *args, **kwargs
          passed through to the request method
        """
        r = await super().request(*a, **kw)

        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            log.warning(f'OPENDOTA responded with an error: {e}')
            backoff_ += 1

            if r.status_code == httpx.codes.TOO_MANY_REQUESTS:
                override = float(r.headers['retry-after'])
            else:
                override = self.burst * backoff_

            await self.wait_for_token(override=override)
            r = await self.request(*a, backoff_=backoff_, **kw)
        else:
            self.tokens = int(r.headers['x-rate-limit-remaining-minute'])
            self.month_tokens = int(r.headers['x-rate-limit-remaining-month'])

        if self.tokens <= 25:
            log.warning(f'approaching rate limit, requests left: {self.tokens}')

        return r

    #

    async def explorer(self, q: str) -> List[Dict]:
        """
        Perform an ad-hoc query to the database.

        Parameters
        ----------
        q : str
          PostgreSQL query to send to OPENDOTA
        """
        r = await self.get('/explorer', params={'sql': q})
        r.raise_for_status()
        return r.json()['rows']

    def __repr__(self) -> str:
        return f'<OpenDotaClient {self.rate}r/s>'
