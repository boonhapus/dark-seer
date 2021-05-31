from typing import List

import httpx

from darkseer.util import RateLimitedHTTPClient
from .schema import (
    GameVersion, Tournament, CompetitiveTeam, Match,
    Hero, HeroHistory, Item, ItemHistory
)


class Stratz(RateLimitedHTTPClient):
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
        super().__init__(tokens=300, seconds=3600, base_url='https://api.stratz.com')

        if bearer_token is not None:
            self.tokens = 500
            self.headers.update({'authorization': f'Bearer {bearer_token}'})

    async def query(self, q: str, **variables) -> httpx.Request:
        """
        Perform a GraphQL query.

        Parameters
        ----------
        q : str
          graphql query to send to Stratz

        **variables
          graphql variables to substitute
        """
        # NOTE:
        #   for some reason, I can't get variables to work with Stratz GraphQL. It
        #   should be as simple as simple passing {'variables': variables} in the data..
        for name, value in variables.items():
            q = q.replace(f'${name}', f'{value}')

        r = await self.post('/graphql', data={'query': q})
        r.raise_for_status()
        return r

    async def patches(self) -> List[GameVersion]:
        """
        Return a list of game versions.
        """
        q = """
        query Patches {
          constants {
            game_version: gameVersions {
              patch_id: id
              patch: name
              release_dt: asOfDateTime
            }
          }
        }
        """
        resp = await self.query(q)
        data = resp.json()['data']['constants']
        return [GameVersion(**v) for v in data['game_version']]

    async def tournaments(self) -> List[Tournament]:
        """
        Return a list of tournaments.
        """
        q = """
        query Tournaments {
          tournaments: leagues(request: {
              skip: $skip_value,
              take: 50,
              tiers: [
                MINOR, MAJOR, INTERNATIONAL,
                DPC_QUALIFIER, DPC_LEAGUE_QUALIFIER, DPC_LEAGUE
              ]
            }) {
            league_id: id
            league_name: displayName
            league_start_date: startDateTime
            league_end_date: endDateTime
            tier
            prize_pool: prizePool
          }
        }
        """
        leagues = []

        while True:
            skip = len(leagues)
            resp = await self.query(q, skip_value=skip)
            data = resp.json()['data']

            for v in data['tournaments']:
                if v not in leagues:
                    leagues.append(v)

            if not data['tournaments']:
                break

        return [Tournament(**v) for v in leagues]

    async def teams(self, *, team_ids: List[int]) -> List[CompetitiveTeam]:
        """
        Return a list of competitive teams.
        """
        q = """
        query CompetitiveTeams {
          competitive_teams: teams(teamIds: $teams) {
            team_id: id
            team_name: name
            team_tag: tag
            created: dateCreated
          }
        }
        """
        resp = await self.query(q, teams=team_ids)
        data = resp.json()['data']
        return [CompetitiveTeam(**v) for v in data['competitive_teams']]

    async def heroes(self, *, patch_id: int=69) -> List[HeroHistory]:
        """
        Return a list of Heroes.
        """
        q = """
        query Heroes {
          constants {
            heroes (gameVersionId: $patch_id, language: ENGLISH) {
              hero_id: id
              hero_internal_name: shortName
              hero_display_name: displayName
              patch_id: gameVersionId
              stats {
                primary_attribute: primaryAttribute
                mana_regen_base: mpRegen
                strength_base: strengthBase
                strength_gain: strengthGain
                agility_base: agilityBase
                agility_gain: agilityGain
                intelligence_base: intelligenceBase
                intelligence_gain: intelligenceGain
                attack_type: attackType
                attack_range: attackRange
                attack_animation: attackAnimationPoint
                base_attack_time: attackRate
                is_captains_mode: cMEnabled
                movespeed: moveSpeed
                turn_rate: moveTurnRate
                armor_base: startingArmor
                magic_armor_base: startingMagicArmor
                damage_base_max: startingDamageMax
                damage_base_min: startingDamageMin
                vision_range_day: visionDaytimeRange
                vision_range_night: visionNighttimeRange

                # true for dire, false for radiant
                is_radiant: team
              }
            }
          }
        }
        """
        resp = await self.query(q, patch_id=patch_id)
        heroes = []

        for hero in resp.json()['data']['constants']['heroes']:
            if hero['stats'] is None:
                continue

            data = {**hero, **hero['stats']}
            data.pop('stats')

            heroes.append(data)

        return [HeroHistory(**v) for v in heroes]

    def __repr__(self) -> str:
        return f'<StratzClient {self.rate}r/s>'
