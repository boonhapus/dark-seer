from typing import List

import httpx

from darkseer.schema import Hero, Item
from darkseer.http import AsyncThrottledClient, AsyncRateLimiter

from .schema import GameVersion


class StratzClient(AsyncThrottledClient):
    """
    Wrapper around the STRATZ REST API.

    Documentation:
        https://docs.stratz.com/

    Rate limit is @ 5,000 requests per hour.
    """
    def __init__(self):
        limiter = AsyncRateLimiter(tokens=5000, seconds=3600, burst=1)
        super().__init__(name='stratz', rate_limiter=limiter)

    @property
    def base_url(self):
        return 'https://api.stratz.com'

    async def _graph_ql_query(self, query: str, **variables) -> httpx.Response:
        """
        Format and send a GraphQL query.

        Parameters
        ----------
        query : str
            SDL to send to the graphql endpoint

        **variables
            var_name: var_value to replace in the SDL. Placeholders are
            denoted with the format $var_name.

        Returns
        -------
        response : httpx.Response
        """
        for name, value in variables.items():
            query = query.replace(f'${name}', f'{value}')

        return await self.post(f'{self.base_url}/graphql', data={'query': query})

    async def patches(self) -> List[GameVersion]:
        """
        Return a list of game versions the Dota 2 game has gone through.

        Parameters
        ----------
        None

        Returns
        -------
        game_versions : List[GameVersion]
        """
        query = """
        {
          game_version: gameVersions {
            patch_id: id
            patch: name
            release_date: asOfDateTime
          }
        }
        """
        r = await self._graph_ql_query(query)
        r.raise_for_status()
        return [GameVersion(**d) for d in r.json()['data']['game_version']]

    async def heroes(self) -> List[Hero]:
        """
        Return a list of current Heroes found in the Dota 2 client.

        Parameters
        ----------
        None

        Returns
        -------
        heroes : List[Hero]
        """
        query = """
        {
          heroes {
            hero_id: id
            display_name: displayName
          }
        }
        """
        raise NotImplementedError('TODO')

    async def items(self) -> List[Item]:
        """
        Return a list of Items found in the Dota 2 client.

        Parameters
        ----------
        None

        Returns
        -------
        items : List[Item]
        """
        query = """
        {
          items {
            id: id
            display_name: displayName
          }
        }
        """
        raise NotImplementedError('TODO')
