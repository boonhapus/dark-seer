from typing import Iterable, List
import asyncio

from darkseer.http import AsyncThrottledClient, AsyncRateLimiter
from darkseer.io import Image


class ValveCDNClient(AsyncThrottledClient):
    """
    Wrapper around the Valve CDN.

    Documentation:
        https://dev.dota2.com/showthread.php?t=58317

    Rate limit is strictly limited @ 1 request per second.
    """
    def __init__(self):
        limiter = AsyncRateLimiter(tokens=1, seconds=1)
        super().__init__(name='opendota', rate_limiter=limiter)

    @property
    def base_url(self):
        return 'http://cdn.dota2.com/apps/dota2'

    async def images(self, uris: Iterable, *, image_type: str) -> List[Image]:
        """
        Retrieve Hero or Item images from the Valve CDN.

        Parameters
        ----------
        uris : Iterable
            uris for the heroes or items to retrieve images for

        image_type : str
            either 'icon' or 'image'

        Returns
        -------
        images : List[Image]
        """
        if image_type == 'icon':
            suffix = 'icon'
        elif image_type == 'image':
            suffix = 'full'
        else:
            raise ValueError(
                f'image_type must be one of "icon" or "image", got {image_type}'
            )

        coros = [
            self.get(f'{self.base_url}/images/heroes/{uri}_{suffix}.png')
            for uri in uris
        ]

        data = [
            {
                'content': r.content,
                'name': f'{uri}_{suffix}',
                'filetype': 'png'
            }
            for r, uri in zip(await asyncio.gather(*coros), uris)
        ]

        return [Image(**d) for d in data]
