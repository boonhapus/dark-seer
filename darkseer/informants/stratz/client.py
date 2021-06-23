from typing import Union, List
import logging
import asyncio

from pydantic import ValidationError
from glom import glom, S, Val, Or, SKIP
import httpx

from darkseer.util import RateLimitedHTTPClient, FileCache, chunks
from .schema import (
    GameVersion, Tournament, CompetitiveTeam, Match, IncompleteMatch,
    HeroHistory, ItemHistory, NPCHistory, AbilityHistory
)
from .parse import parse_events
from .spec import (
    PATCH_SPEC, HERO_SPEC, ITEM_SPEC, NPC_SPEC, ABILITY_SPEC,
    TEAM_SPEC, TOURNAMENT_SPEC, MATCH_SPEC
)


log = logging.getLogger(__name__)
_cache = FileCache('C:/projects/dark-seer/scripts/cache')


class Stratz(RateLimitedHTTPClient):
    """
    Wrapper around the STRATZ REST API.

    Documentation:
        https://docs.stratz.com/
        https://api.stratz.com/graphiql

    [ANON] Rate limit is 300/hour, 150/minute @ 20 requests per second.
    [AUTH] Rate limit is 500/hour, 150/minute @ 20 requests per second.

    Parameters
    ----------
    bearer_token : str, default None
        token in the format "Bearer XXXXXX..."
        if supplied, elevates the per-hour rate limit
    """
    def __init__(self, bearer_token: str=None):
        super().__init__(tokens=300, seconds=3600, base_url='https://api.stratz.com', timeout=None)

        if bearer_token is not None:
            if not bearer_token.startswith('Bearer '):
                bearer_token = f'Bearer {bearer_token}'

            log.info('setting bearer token and raising rate limit to 500req/hr')
            self.tokens = 500
            self.headers.update({'authorization': bearer_token})

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        if self.tokens < 500:
            log.info(f'done with API work... there are {self.tokens} tokens left this hour')

        return await super().__aexit__(exc_type, exc_value, traceback)

    #

    @property
    def burst(self) -> float:
        """
        STRATZ allows a 150req/min burst.
        """
        return 150 / 60

    async def wait_for_token(self, *, override: float=None) -> None:
        """
        Block the context until a token is available.
        """
        await asyncio.sleep(override or self.burst)

    async def request(self, *a, backoff_: int=0, **kw) -> httpx.Response:
        """
        Make a request, adjusting tokens if necessary.

        Parameters
        ----------
        backoff_ : int, default 0
          linear factor to wait in between retries in case of an error

        *args, **kwargs
          passed through to the request method
        """
        r = await super().request(*a, **kw)

        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            log.warning(f'STRATZ responded with an error: {e}')
            backoff_ += 1

            if r.status_code == httpx.codes.TOO_MANY_REQUESTS:
                override = float(r.headers['retry-after'])
            else:
                override = self.burst * backoff_

            await self.wait_for_token(override=override)
            r = await self.request(*a, backoff_=backoff_, **kw)
        else:
            self.tokens = int(r.headers['x-ratelimit-remaining-hour'])

        if self.tokens <= 25:
            log.warning(f'approaching rate limit, requests left: {self.tokens}')

        return r

    #

    @_cache.memoize
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
            gameVersions {
              id
              name
              asOfDateTime
            }
          }
        }
        """
        resp = await self.query(q)
        spec = ('data.constants.gameVersions', [PATCH_SPEC])
        data = glom(resp.json(), spec)
        return [GameVersion(**v) for v in data]

    async def heroes(self, *, patch_id: int=69) -> List[HeroHistory]:
        """
        Return a list of heroes.

        Parameters
        ----------
        patch_id : int
          game version to get hero stats on
        """
        q = """
        query Heroes {
          constants {
            heroes (gameVersionId: $patch_id, language: ENGLISH) {
              id
              gameVersionId
              shortName
              displayName
              parse_stats: stats {
                primaryAttribute
                mpRegen
                strengthBase
                strengthGain
                agilityBase
                agilityGain
                intelligenceBase
                intelligenceGain
                attackRate
                attackAnimationPoint
                attackType
                attackRange
                cMEnabled
                moveSpeed
                moveTurnRate
                startingArmor
                startingMagicArmor
                startingDamageMax
                startingDamageMin
                visionDaytimeRange
                visionNighttimeRange

                # true for dire, false for radiant
                team
              }
            }
          }
        }
        """
        resp = await self.query(q, patch_id=patch_id)
        spec = ('data.constants.heroes', [Or(HERO_SPEC, default=SKIP)])
        data = glom(resp.json(), spec)
        return [HeroHistory(**v) for v in data]

    async def items(self, *, patch_id: int=69) -> List[ItemHistory]:
        """
        Return a list of items.

        Parameters
        ----------
        patch_id : int
          game version to get item stats on
        """
        q = """
        query Items {
          constants {
            items (gameVersionId: $patch_id, language: ENGLISH) {
              id
              shortName
              displayName
              parse_stats: stat {
                cost
                isRecipe
                isSideShop
                quality
                unitTargetFlags
                unitTargetTeam
                unitTargetType
              }
            }
          }
        }
        """
        resp = await self.query(q, patch_id=patch_id)
        # 1. Record patch_id at higher scope
        # 2. Navigate down the path to all the item data
        # 3. Apply the ITEM_SPEC to each item
        #    a. SKIP data points that don't pass the spec
        spec = (
            S(patch_id=Val(patch_id)),
            'data.constants.items',
            [Or(ITEM_SPEC, default=SKIP)]
        )
        data = glom(resp.json(), spec)
        return [ItemHistory(**v) for v in data]

    async def npcs(self, *, patch_id: int=69) -> List[NPCHistory]:
        """
        Return a list of npcs.

        Parameters
        ----------
        patch_id : int
          game version to get npc stats on
        """
        q = """
        query NPCs {
          constants {
            npcs (gameVersionId: $patch_id) {
              id
              name
              parse_stats: stat {
                combatClassAttack
                combatClassDefend
                isAncient
                isNeutralUnitType
                statusHealth
                statusMana
                teamName
                unitRelationshipClass
              }
            }
          }
        }
        """
        resp = await self.query(q, patch_id=patch_id)
        # 1. Record patch_id at higher scope
        # 2. Navigate down the path to all the NPC data
        # 3. Apply the NPC_SPEC to each NPC
        #    a. SKIP data points that don't pass the spec
        spec = (
            S(patch_id=Val(patch_id)),
            'data.constants.npcs',
            [Or(NPC_SPEC, default=SKIP)]
        )
        data = glom(resp.json(), spec)
        return [NPCHistory(**v) for v in data]

    async def abilities(self, *, patch_id: int=69) -> List[AbilityHistory]:
        """
        Return a list of abilities.

        Parameters
        ----------
        patch_id : int
          game version to get ability stats on
        """
        q = """
        query Abilities {
          constants {
            abilities (gameVersionId: $patch_id, language: ENGLISH) {
              id
              name
              parse_language: language {
                displayName
              }
              isTalent
              parse_stats: stat {
                hasScepterUpgrade
                isGrantedByScepter
                isGrantedByShard
                isUltimate
                requiredLevel
                type
                unitDamageType
                unitTargetFlags
                unitTargetTeam
                unitTargetType
              }
            }
          }
        }
        """
        resp = await self.query(q, patch_id=patch_id)
        # 1. Record patch_id at higher scope
        # 2. Navigate down the path to all the ability data
        # 3. Apply the ABILITY_SPEC to each ability
        #    a. SKIP data points that don't pass the spec
        spec = (
            S(patch_id=Val(patch_id)),
            'data.constants.abilities',
            [Or(ABILITY_SPEC, default=SKIP)]
        )
        data = glom(resp.json(), spec)
        return [AbilityHistory(**v) for v in data]

    async def reparse(self, *, replay_salts: List[int]) -> None:
        """
        Ask STRATZ to reparse a given replay.

        Parameters
        ----------
        replay_salts : list[int, ...]
          matches to reparse
        """
        q = """
        query {
          stratz {
            matchRetry(id: $replay_salt)
          }
        }
        """
        for salt in replay_salts:
            r = await self.query(q, replay_salt=salt)
            r = r.json()['data']['stratz']['matchRetry']
            log.info(f'reparsing salt, {salt}: {r}')

    async def teams(self, *, team_ids: List[int]) -> List[CompetitiveTeam]:
        """
        Return a list of competitive teams.

        Parameters
        ----------
        team_ids : List[int, ...]
          ids of teams to parse
        """
        q = """
        query CompetitiveTeams {
          competitive_teams: teams(teamIds: $teams) {
            id
            name
            tag
            dateCreated
          }
        }
        """
        resp = await self.query(q, teams=team_ids)
        spec = ('data.competitive_teams', [TEAM_SPEC])
        data = glom(resp.json(), spec)
        return [CompetitiveTeam(**v) for v in data]

    async def tournaments(self) -> List[Tournament]:
        """
        Return a list of tournaments.
        """
        q = """
        query Tournaments {
          leagues(request: {
              skip: $skip_value,
              take: 50,
              tiers: [
                MINOR, MAJOR, INTERNATIONAL,
                DPC_QUALIFIER, DPC_LEAGUE_QUALIFIER, DPC_LEAGUE
              ]
            }) {
            id
            displayName
            startDateTime
            endDateTime
            tier
            prizePool
          }
        }
        """
        leagues = []

        while True:
            skip = len(leagues)
            resp = await self.query(q, skip_value=skip)
            spec = ('data.leagues', [TOURNAMENT_SPEC])
            data = glom(resp.json(), spec)
            leagues.extend([d for d in data if d not in leagues])

            if not data:
                break

        return [Tournament(**v) for v in leagues]

    async def tournament_matches(self, *, league_id: int) -> List[Union[Match, IncompleteMatch]]:
        """
        Return a list of Matches for a given tournament.

        Matches returned will either be fully parsed and of type
        stratz.schema.Match, or an error was found while parsing and
        will be of type stratz.schema.IncompleteMatch.

        Parameters
        ----------
        league_id : int
          tournament to parse matches from
        """
        # Match is a composable object.
        # Match.tournament ...... Tournament
        # Match.teams ........... CompetitiveTeam
        # Match.accounts ........ Account
        # Match.draft ........... MatchDraft
        # Match.players ......... MatchPlayer
        # Match.hero_movements .. HeroMovement
        # Match.events .......... MatchEvent
        q = """
        query TournamentMatches {
          league(id: $league_id) {
            matches(request: {
              skip: $skip_value,
              take: 50,
              isParsed: true
            }) {
              id
            }
          }
        }
        """
        match_ids = set()

        # Get all Match IDs for all tournaments.
        while True:
            skip = len(match_ids)
            resp = await self.query(q, league_id=league_id, skip_value=skip)
            spec = ('data.league.matches', ['id'])
            data = glom(resp.json(), spec)
            match_ids.update(data)

            if not data:
                break

        matches = []

        # Get all matches
        for chunk in chunks(match_ids, n=10):
            r = await self.matches(match_ids=chunk)
            matches.extend(r)

        return matches

    async def matches(self, *, match_ids: List[int]) -> List[Union[Match, IncompleteMatch]]:
        """
        Return a list of Matches.

        Matches returned will either be fully parsed and of type
        stratz.schema.Match, or an error was found while parsing and
        will be of type stratz.schema.IncompleteMatch.

        Parameters
        ----------
        match_ids : List[int, ...]
          ids of matches to parse
        """
        # Match is a composable object.
        # Match.tournament ...... Tournament
        # Match.teams ........... CompetitiveTeam
        # Match.accounts ........ Account
        # Match.draft ........... MatchDraft
        # Match.players ......... MatchPlayer
        # Match.hero_movements .. HeroMovement
        # Match.events .......... MatchEvent
        q = """
        query Matches {
          matches: matches(ids: $match_ids) {
            id
            replaySalt
            gameVersionId
            leagueId
            seriesId
            radiantTeamId
            direTeamId
            startDateTime
            isStats
            didRadiantWin
            durationSeconds
            regionId
            lobbyType
            gameMode

            parse_league: league {
              id
              displayName
              startDateTime
              endDateTime
              tier
              prizePool
            }
            parse_radiant: radiantTeam {
              id
              name
              tag
              countryCode
              dateCreated
            }
            parse_dire: direTeam {
              id
              name
              tag
              countryCode
              dateCreated
            }
            parse_match_draft: stats {
              pick_bans: pickBans {
                # match_id:
                heroId
                # draft_type:
                order
                # is_random:
                # by_steam_id:
                # extra data for parsing
                playerIndex
                isPick
                bannedHeroId
                wasBannedSuccessfully
              }
            }
            parse_accounts: players {
              parse_account: steamAccount {
                id
                name
                proSteamAccount {
                  name
                }
              }
            }
            parse_hero_movements: players {
              heroId
              playbackData {
                playerUpdatePositionEvents {
                  # match_id:
                  # hero_id:
                  # id:
                  time
                  x
                  y
                }
              }
            }
            parse_match_players: players {
              # match_id
              heroId
              steamAccountId
              playerSlot
              partyId
              leaverStatus
              # extra data for parsing
              isRandom
            }
            parse_player_events: players {
              playbackData {
                killEvents {
                  time
                  positionX
                  positionY
                  byAbility
                  byItem
                  attacker
                  target
                  # extra data
                  isFromIllusion
                }
                deathEvents {
                  time
                  positionX
                  positionY
                  byAbility
                  byItem
                  attacker
                  target
                  # extra data
                  isFromIllusion
                  goldFed
                  goldLost
                  reliableGold
                  unreliableGold
                  timeDead
                }
                assistEvents {
                  time
                  positionX
                  positionY
                  attacker
                  target
                }
              }
            }
          }
        }
        """
        resp = await self.query(q, match_ids=match_ids)
        matches = []

        for match in resp.json()['data']['matches']:

            # pre-processing
            match['parse_teams'] = [match['parse_dire'], match['parse_radiant']]

            try:
                m = glom(match, MATCH_SPEC)

                # handled in glomspec
                # m['tournament']
                # m['teams']
                # m['accounts']
                # m['hero_movements']
                # m['players']
                #
                m['events'] = parse_events(match)

                # TODO .. remove print-data-debugging
                # from rich import print
                # for event_type in set(e['event_type'] for e in m['events']):
                #     events = [e for e in m['events'] if e['event_type'] == event_type]
                #     print(f'{event_type}: {len(events)} events')
                # raise SystemExit(-1)

                m = Match(**m)
            except ValidationError:
                log.exception(f'missing data on match {match["id"]}')
                m = IncompleteMatch(match_id=match['id'], replay_salt=match['replaySalt'])

            matches.append(m)

        return matches

    def __repr__(self) -> str:
        return f'<StratzClient {self.rate}r/s>'
