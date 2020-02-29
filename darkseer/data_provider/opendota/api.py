from typing import List

from httpx import HTTPError

from darkseer.schema import Hero
from darkseer.http import AsyncThrottledClient, AsyncRateLimiter


class SQLQueryError(Exception):
    """
    TODO
    """
    def __init__(self, *args, query, response):
        self.query = query
        self.response = response


class OpenDotaClient(AsyncThrottledClient):
    """
    TODO
    """
    def __init__(self):
        limiter = AsyncRateLimiter(tokens=60, seconds=60, burst=1)
        super().__init__(name='opendota', rate_limiter=limiter)

    @property
    def base_url(self):
        return 'https://api.opendota.com/api'

    async def explorer(self, sql: str) -> List[dict]:
        """
        TODO
        """
        r = await self.get(f'{self.base_url}/explorer', params=f'sql={sql}')
        data = r.json()

        try:
            return data['rows']
        except KeyError as e:
            code, *_ = e.args[0].split(':')
            err_divider_loc = data['err'].rfind('-')
            txt = data['err'][err_divider_loc:]
            raise SQLQueryError(f'{code} {txt}', query=sql, response=r) from None
