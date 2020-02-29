from typing import List

from darkseer.schema import Hero
from darkseer.http import AsyncThrottledClient, AsyncRateLimiter

from .schema import GameVersion


class StratzClient(AsyncThrottledClient):
    """
    TODO
    """
    def __init__(self):
        limiter = AsyncRateLimiter(tokens=5000, seconds=3600, burst=1)
        super().__init__(name='stratz', rate_limiter=limiter)

    @property
    def base_url(self):
        return 'https://api.stratz.com'

    async def patches(self) -> List[GameVersion]:
        """
        TODO
        """
        q = """
        {
          game_version: gameVersions {
            id
            patch: name
            release_date: asOfDateTime
          }
        }
        """
        r = await self.post(f'{self.base_url}/GraphQL', data={'query': q})
        r.raise_for_status()
        return [GameVersion(**gv) for gv in r.json()['data']['game_version']]

    async def heroes(self) -> List[Hero]:
        """
        TODO
        """
        pass

    async def hero(self, id: int) -> Hero:
        """
        TODO
        """
        pass
