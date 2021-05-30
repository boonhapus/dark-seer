from typing import Union, List
import asyncio
import enum

from pydantic import validate_arguments

from darkseer.schema import Hero, Item
from darkseer.http import AsyncThrottledClient, AsyncRateLimiter
from darkseer.io import Image


class ImageType(str, enum.Enum):
    icon = 'icon'
    full = 'image'


class ValveCDNClient(AsyncThrottledClient):
    """
    Wrapper around the Valve CDN.

    Documentation:
        https://dev.dota2.com/showthread.php?t=58317

    Rate limit is strictly limited @ 1 request per second.
    """
    def __init__(self):
        limiter = AsyncRateLimiter(tokens=1, seconds=1)
        super().__init__(name='valve', rate_limiter=limiter)

    @property
    def base_url(self):
        return 'http://cdn.dota2.com/apps/dota2'

    @validate_arguments
    async def images(self, entities: List[Hero], *, image_type: ImageType) -> List[Image]:
        """
        Retrieve Hero images from the Valve CDN.

        Parameters
        ----------
        entities : Iterable[str]
            entities for the heroes to retrieve images for

        image_type : str
            either 'icon' or 'image'

        Returns
        -------
        images : List[Image]
        """
        endpoint = f'{self.base_url}/images/heroes'
        img_calls = []

        for entity in entities:
            headers = {'fname': entity.display_name}
            url = f'{endpoint}/{entity.uri}_{image_type.name}.png'
            img_calls.append(self.get(url, headers=headers))

        for coro in asyncio.as_completed(img_calls):
            r = await coro
            yield Image(r.content, name=r.request.headers['fname'], filetype='png')
