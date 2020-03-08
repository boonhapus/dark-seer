from typing import List, Union
import asyncio

import httpx

from darkseer.schema import Hero, Item, Match, Tournament
from darkseer.http import AsyncThrottledClient, AsyncRateLimiter

from .schema import GameVersion


class StratzClient(AsyncThrottledClient):
    """
    Wrapper around the STRATZ REST API.

    Documentation:
        https://docs.stratz.com/

    [ANON] Rate limit is 2,500/day, 500/hour @ 10 requests per second.
    [AUTH] Rate limit is 5,000/day, 500/hour @ 10 requests per second.

    Attributes
    ----------
    bearer_token : str, default None
        token in the format "Bearer XXXXXX..."
        if supplied, elevates the per-day rate limit from 2,500 to 5,000
    """
    def __init__(self, bearer_token: str=None):
        if bearer_token is not None:
            opts = {
                'headers': {
                    'authorization': bearer_token
                }
            }
        else:
            opts = {}

        limiter = AsyncRateLimiter(tokens=10, seconds=1, burst=1)
        super().__init__(name='stratz', rate_limiter=limiter, **opts)

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
        raise NotImplementedError('TODO: need to finalize schema.Hero')

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
        raise NotImplementedError('TODO: need to finalize schema.Item')

    async def tournaments(self, tiers: Union[List, int]=None) -> List[Tournament]:
        """
        Returns the list of tracked Leagues.

        Tiers are listed in incrementing order:
          1 - Amateur
          2 - Professional
          3 - DPC Minors
          4 - DPC Majors
          5 - The International

        Parameters
        ----------
        tiers : list or int, default [3, 4, 5]
            filter applied to league divisions

        Returns
        -------
        leagues : List[LeagueInfo]
        """
        if tiers is None:
            tiers = [3, 4, 5]
        else:
            try:
                tiers = list(tiers)
            except TypeError:
                pass

        query = """
        {
          tournaments: leagues(tiers: $tiers) {
            league_id: id
            league_name: displayName
            league_start_date: startDateTime
            league_end_date: endDateTime
            prize_pool: prizePool
          }
        }
        """
        r = await self._graph_ql_query(query, tiers=tiers)
        r.raise_for_status()

        # TODO: remove all below in favor of a GraphQL-only query. right now,
        #       we're making N api calls where..
        #
        #           N = len(tournaments.matches) + 1
        #
        #       ..when this really could be N = 2. One pass to /graphql for all
        #       the tournaments, and then another to grab all the matches for
        #       the returned League IDs in call #1.
        #
        #       We'll still need to reformat into the <data> list below, but
        #       that's no big deal. ;)
        #
        #       STATZ.Keo researching as of 2020/03/09
        #
        league_info = r.json()['data']['tournaments']

        coros = [
            self.get(f'{self.base_url}/api/v1/league/{d["league_id"]}/matches')
            for d in league_info
        ]

        data = [
            {**league, 'match_ids': [m['id'] for m in r.json()]}
            for r, league in zip(await asyncio.gather(*coros), league_info)
        ]

        return [Tournament.parse_obj(d) for d in data]

    async def match(self, match_id: int) -> Match:
        """
        """
        query = """{
          matches(ids: [5212485721]) {
            match_id: id
            patch_id: gameVersionId
            league_id: leagueId
            series_id: seriesId
            start_datetime: startDateTime
            duration: durationSeconds
            region: regionId
            lobby_type: lobbyType
            game_mode: gameMode
            average_rank: averageRank
            is_radiant_win: didRadiantWin
          }
        }"""
        raise NotImplementedError('TODO: need to finalize schema.Item')
