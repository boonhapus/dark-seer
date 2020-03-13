from typing import Union
import ayncio

from darkseer.models import Hero
from darkseer.http import AsyncThrottledClient, AsyncRateLimiter


class ValveCDNClient(AsyncThrottledClient):
    """
    Wrapper around the Valve CDN.

    Documentation:
        https://dev.dota2.com/showthread.php?t=58317

    Rate limit is strictly limited @ 1 request per second.
    """
    def __init__(self):
        limiter = AsyncRateLimiter(tokens=1, seconds=1, burst=1)
        super().__init__(name='opendota', rate_limiter=limiter)

    @property
    def base_url(self):
        return 'http://cdn.dota2.com/apps/dota2'

    async def minimap_icons(self, db):
        """
        """
        async with db.session() as sess:
            heroes = await sess.query(Hero.uri).all()

        coros = [
            self.get(f'{self.base_url}/images/heroes/{uri}_icon.png')
            for uri in heroes
        ]

        r = await asyncio.gather(*coros)
        return r

    async def images(self, hero: Union[Hero, int]):
        """
        """
        pass