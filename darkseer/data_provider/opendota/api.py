from typing import List

from httpx import HTTPError

from darkseer.http import AsyncThrottledClient, AsyncRateLimiter


class SQLQueryError(HTTPError):
    """
    Raised when an error occurs when compiling the SQL query.

    Attributes
    ----------
    msg : str
        exception message

    query : str
        attempted query sent in the request

    response : httpx.Response
        response object returned from httpx.request
    """
    def __init__(self, *args, query, response):
        self.query = query
        super().__init__(*args, response=response)


class OpenDotaClient(AsyncThrottledClient):
    """
    Wrapper around the OpenDotA REST API.

    Documentation:
        https://docs.opendota.com/

    Rate limit is 50,000 per month @ 60 requests per minute.
    """
    def __init__(self):
        limiter = AsyncRateLimiter(tokens=60, seconds=60, burst=1)
        super().__init__(name='opendota', rate_limiter=limiter)

    @property
    def base_url(self):
        return 'https://api.opendota.com/api'

    async def explorer(self, sql: str) -> List[dict]:
        """
        Submit arbitrary SQL queries to the database.

        Run advanced queries on professional matches (excludes amateur
        leagues).

        Parameters
        ----------
        sql : str
            a PostgreSQL query

        Returns
        -------
        data_points : List[dict]
        """
        r = await self.get(f'{self.base_url}/explorer', params=f'sql={sql}')
        data = r.json()

        try:
            return data['rows']
        except KeyError as e:
            code, *_ = e.args[0].split(':')
            err_divider_loc = data['err'].rfind('-')
            txt = data['err'][err_divider_loc:]
            msg = f'{code} {txt}\n\n{sql}'
            raise SQLQueryError(msg, query=sql, response=r) from None
