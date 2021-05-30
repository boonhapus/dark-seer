from typing import List, Union
import collections
import itertools as it

import httpx

from darkseer.schema import Hero, Item, Tournament
from darkseer.http import AsyncThrottledClient, AsyncRateLimiter

from .schema import GameVersion, Match


class StratzClient(AsyncThrottledClient):
    """
    Wrapper around the STRATZ REST API.

    Documentation:
        https://docs.stratz.com/

    [ANON] Rate limit is 300/hour, 150/minute @ 20 requests per second.
    [AUTH] Rate limit is 500/hour, 150/minute @ 20 requests per second.

    Attributes
    ----------
    bearer_token : str, default None
        token in the format "Bearer XXXXXX..."
        if supplied, elevates the per-hour rate limit
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

        limiter = AsyncRateLimiter(tokens=20, seconds=1)
        super().__init__(name='stratz', rate_limiter=limiter, **opts)

    @property
    def base_url(self):
        return 'https://api.stratz.com'

    def _sanitize_gql_query(self, query: str, **variables) -> str:
        """
        Format a GraphQL query, replacing variables.

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

        return query.replace("'", "")

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
          constants {
            heroes {
              hero_id: id
              display_name: displayName
              uri: shortName
            }
          }
        }
        """
        r = await self._gql_query(query)
        r.raise_for_status()
        return [Hero(**d) for d in r.json()['data']['constants']['heroes']]

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
          constants {
            items {
              item_id: id
              display_name: displayName
              uri: shortName
            }
          }
        }
        """
        r = await self._gql_query(query)
        r.raise_for_status()
        return [Item(**d) for d in r.json()['data']['constants']['items']]

    async def tournaments(self, tiers: Union[List, str]=None) -> List[Tournament]:
        """
        Return a list of tracked Leagues.

        Available tiers:
          Amateur
          Professional
          Premium      (aka DPC Minors)
          Pro Circuit  (aka DPC Majors)
          Main Event   (aka The International)

        Parameters
        ----------
        tiers : list or str, default ['PREMIUM', 'PRO_CIRCUIT', 'MAIN_EVENT']
            filter applied to league divisions

        Returns
        -------
        leagues : List[LeagueInfo]
        """
        if tiers is None:
            tiers = ['PREMIUM', 'PRO_CIRCUIT', 'MAIN_EVENT']
        elif isinstance(tiers, str):
            tiers = [tiers.replace(' ', '_').upper()]
        else:
            tiers = [t.replace(' ', '_').upper() for t in tiers]

        # NOTE:
        #
        #   We make 2 requests to the GraphQL endpoint here. Once to grab all
        #   the leagues that match the <tiers> criteria and then once again to
        #   grab up to 1000 matches for EACH league_id. After some reformatting
        #   of the returned data, we can get to all the match_ids per
        #   tournament.
        #

        query = """
        {
          tournaments: leagues(request: {tiers: $tiers}) {
            league_id: id
            league_name: displayName
            league_start_date: startDateTime
            league_end_date: endDateTime
            prize_pool: prizePool
          }
        }
        """
        r = await self._gql_query(query, tiers=tiers)
        r.raise_for_status()

        league_info = r.json()['data']['tournaments']

        GQL_FMT = """
          league_$id: league(id: $id) {
            matches(request: {skip: 0, take: 1000}) {
              match_id: id
              league_id: leagueId
            }
          }
        """
        # No tournament has over 500 matches as of writing (2020/03/23), so
        # 1000 matches per tournament should be totally fine for now.
        queries = '\n'.join([
            self._sanitize_gql_query(GQL_FMT, id=data['league_id'])
            for data in league_info
        ])

        r = await self._gql_query('{$q}', q=queries)
        r.raise_for_status()

        # This is not very pretty...
        #
        collect = collections.defaultdict(list)

        match_data = it.chain.from_iterable(
                         data
                         for v in r.json()['data'].values()
                         for data in v.values()
                     )

        for match in match_data:
            m = match['match_id']
            t = match['league_id']
            collect[t].append(m)

        data = [
            {**league, 'match_ids': collect[league['league_id']]}
            for league in league_info
        ]
        #
        # can we do better ... ?

        return [Tournament.parse_obj(d) for d in data]

    async def matches(self, *match_ids: int) -> List[Match]:
        """
        Return a single Match.
        """
        query = """
        {
          matches(ids: $match_ids) {
            match_id: id
            region: regionId
            lobby_type: lobbyType
            game_mode: gameMode
            patch_id: gameVersionId
            start_datetime: startDateTime
            duration: durationSeconds
            is_radiant_win: didRadiantWin
            is_stats: isStats
            league_id: leagueId
            series_id: seriesId
            radiant_team_id: radiantTeamId
            dire_team_id: direTeamId
            rank: actualRank
            players {
              steam_id: steamAccountId
            }
            stats {
              draft: pickBans {
                is_pick: isPick
                banned: wasBannedSuccessfully
                by_player_index: playerIndex
                picked_hero_id: heroId
                banned_hero_id: bannedHeroId
                draft_order: order
              }
            }
          }
        }
        """
        r = await self._gql_query(query, match_ids=list(match_ids))
        return [Match.parse_obj(m) for m in r.json()['data']['matches']]
