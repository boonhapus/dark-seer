from typing import List, Union
import collections
import itertools as it

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

    def _sanitize_gql_query(self, query: str, **variables) -> str:
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
        sanitized_query : str
        """
        for name, value in variables.items():
            query = query.replace(f'${name}', f'{value}')

        return query

    async def _gql_query(self, query: str, **variables) -> httpx.Response:
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
        query = self._sanitize_gql_query(query, **variables)
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
        r = await self._gql_query(query)
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
        Return a list of tracked Leagues.

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

        # NOTE:
        #
        #   We make 2 requests to the GraphQL endpoint here. Once to grab all
        #   the leagues that match the <tiers> criteria and then once again to
        #   grab 3 pages worth (up to 750 records) of matches for EACH
        #   league_id. After some reformatting of the returned data, we can get
        #   to all the match_ids per tournament.
        #

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
        r = await self._qql_query(query, tiers=tiers)
        r.raise_for_status()

        league_info = r.json()['data']['tournaments']

        GQL_FMT = """
          matches_$id_$e: leagueMatches(request: {skip: $begin, take: 250, leagueId: $id}) {
            match_id: id
            league_id: leagueId
          }
        """
        # We're kind abusing the GraphQL parameters here. <begin> will be a
        # few values: 0, 250, 500 which will grab up to 750 matches in a single
        # query. No tournament has over 500 matches as of writing (2020/03/10),
        # so 750 matches per tournament should be totally fine for now.
        queries = '\n'.join([
            self._sanitize_gql_query(GQL_FMT, begin=n, id=data['league_id'], e=e)
            for data in league_info
            for e, n in enumerate(range(0, 750, 250))
        ])

        r = await self._gql_query('{$q}', q=queries)
        r.raise_for_status()

        matches = collections.defaultdict(list)

        for match in list(it.chain.from_iterable(r.json()['data'].values())):
            m = match['match_id']
            t = match['league_id']
            matches[t].append(m)

        data = [
            {**league, 'match_ids': matches[league['league_id']]}
            for league in league_info
        ]

        return [Tournament.parse_obj(d) for d in data]

    async def match(self, match_id: int) -> Match:
        """
        Return a single Match.
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
