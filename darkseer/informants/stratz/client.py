from typing import Union, List
import logging
import asyncio

from pydantic import ValidationError
from glom import glom, Val, Or, SKIP
import httpx

from darkseer.util import RateLimitedHTTPClient, FileCache, chunks
from .schema import (
    GameVersion, Tournament, CompetitiveTeam, Match, IncompleteMatch,
    HeroHistory, ItemHistory, NPCHistory, AbilityHistory
)
from .parse import (
    parse_teams, parse_draft, parse_accounts, parse_players, parse_hero_movements
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
        spec = (
            'data.constants.gameVersions', [{
                'patch_id': 'id',
                'patch': 'name',
                'release_datetime': 'asOfDateTime'
            }]
        )
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
              hero_id: id
              hero_internal_name: shortName
              hero_display_name: displayName
              patch_id: gameVersionId
              parse_stats: stats {
                primary_attribute: primaryAttribute
                mana_regen_base: mpRegen
                strength_base: strengthBase
                strength_gain: strengthGain
                agility_base: agilityBase
                agility_gain: agilityGain
                intelligence_base: intelligenceBase
                intelligence_gain: intelligenceGain
                base_attack_time: attackRate
                attack_point: attackAnimationPoint
                attack_type: attackType
                attack_range: attackRange
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
                faction: team
              }
            }
          }
        }
        """
        HERO_SPEC = {
            'hero_id': 'hero_id',
            'patch_id': 'patch_id',
            'hero_internal_name': 'hero_internal_name',
            'hero_display_name': 'hero_display_name',
            'primary_attribute': 'parse_stats.primary_attribute',
            'mana_regen_base': 'parse_stats.mana_regen_base',
            'strength_base': 'parse_stats.strength_base',
            'strength_gain': 'parse_stats.strength_gain',
            'agility_base': 'parse_stats.agility_base',
            'agility_gain': 'parse_stats.agility_gain',
            'intelligence_base': 'parse_stats.intelligence_base',
            'intelligence_gain': 'parse_stats.intelligence_gain',
            'base_attack_time': 'parse_stats.base_attack_time',
            'attack_point': 'parse_stats.attack_point',
            'attack_range': 'parse_stats.attack_range',
            'attack_type': 'parse_stats.attack_type',
            'is_captains_mode': 'parse_stats.is_captains_mode',
            'movespeed': 'parse_stats.movespeed',
            'turn_rate': 'parse_stats.turn_rate',
            'armor_base': 'parse_stats.armor_base',
            'magic_armor_base': 'parse_stats.magic_armor_base',
            'damage_base_max': 'parse_stats.damage_base_max',
            'damage_base_min': 'parse_stats.damage_base_min',
            'faction': 'parse_stats.faction',
            'vision_range_day': 'parse_stats.vision_range_day',
            'vision_range_night': 'parse_stats.vision_range_night'
        }

        # skip items if they error out
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
        ITEM_SPEC = {
            'item_id': 'id',
            'patch_id': Val(patch_id),
            'item_internal_name': 'shortName',
            'item_display_name': 'displayName',
            'cost': 'parse_stats.cost',
            'is_recipe': 'parse_stats.isRecipe',
            'is_side_shop': 'parse_stats.isSideShop',
            'quality': 'parse_stats.quality',
            'unit_target_flags': 'parse_stats.unitTargetFlags',
            'unit_target_team': 'parse_stats.unitTargetTeam',
            'unit_target_type': 'parse_stats.unitTargetType'
        }

        # skip items if they error out
        resp = await self.query(q, patch_id=patch_id)
        spec = ('data.constants.items', [Or(ITEM_SPEC, default=SKIP)])
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
        NPC_SPEC = {
            'npc_id': 'id',
            'patch_id': Val(patch_id),
            'npc_internal_name': 'name',
            'combat_class_attack': 'parse_stats.combatClassAttack',
            'combat_class_defend': 'parse_stats.combatClassDefend',
            'is_ancient': 'parse_stats.isAncient',
            'is_neutral': 'parse_stats.isNeutralUnitType',
            'health': 'parse_stats.statusHealth',
            'mana': 'parse_stats.statusMana',
            'faction': 'parse_stats.teamName',
            'unit_relationship_class': 'parse_stats.unitRelationshipClass'
        }

        # skip items if they error out
        resp = await self.query(q, patch_id=patch_id)
        spec = ('data.constants.npcs', [Or(NPC_SPEC, default=SKIP)])
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
        ABILITY_SPEC = {
            'ability_id': 'id',
            'patch_id': Val(patch_id),
            'ability_internal_name': 'name',
            'ability_display_name': 'parse_language.displayName',
            'is_talent': 'isTalent',
            'is_ultimate': 'parse_stats.hasScepterUpgrade',
            'has_scepter_upgrade': 'parse_stats.isGrantedByScepter',
            'is_scepter_upgrade': 'parse_stats.isGrantedByShard',
            'is_aghanims_shard': 'parse_stats.isUltimate',
            'required_level': 'parse_stats.requiredLevel',
            'ability_type': 'parse_stats.type',
            'ability_damage_type': 'parse_stats.unitDamageType',
            'unit_target_flags': 'parse_stats.unitTargetFlags',
            'unit_target_team': 'parse_stats.unitTargetTeam',
            'unit_target_type': 'parse_stats.unitTargetType',
        }
        resp = await self.query(q, patch_id=patch_id)
        spec = ('data.constants.abilities', [Or(ABILITY_SPEC, default=SKIP)])
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
            id
            displayName
            startDateTime
            endDateTime
            tier
            prizePool
          }
        }
        """
        TOURNAMENT_SPEC = {
            'league_id': 'id',
            'league_name': 'displayName',
            'league_start_date': 'startDateTime',
            'league_end_date': 'endDateTime',
            'tier': 'tier',
            'prize_pool': 'prizePool'
        }
        leagues = []

        while True:
            skip = len(leagues)
            resp = await self.query(q, skip_value=skip)
            spec = ('data.tournaments', [TOURNAMENT_SPEC])
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
          tournament_matches: league(id: $league_id) {
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
            spec = ('data.tournament_matches.matches', ['id'])
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
              team_id: id
              team_name: name
              team_tag: tag
              country_code: countryCode
              created: dateCreated
            }
            parse_dire: direTeam {
              team_id: id
              team_name: name
              team_tag: tag
              country_code: countryCode
              created: dateCreated
            }
            parse_match_players: players {
              # match_id
              hero_id: heroId
              steam_id: steamAccountId
              slot: playerSlot
              party_id: partyId
              is_leaver: leaverStatus
              # extra data for parsing
              isRandom
              acct: steamAccount {
                steam_id: id
                steam_name: name
                is_pro: proSteamAccount {
                  steam_name: name
                }
              }
              hero_movement: playbackData {
                positions: playerUpdatePositionEvents {
                  # match_id:
                  # hero_id:
                  # id:
                  time
                  x
                  y
                }
              }
            }
            parse_match_draft: stats {
              pick_bans: pickBans {
                # match_id:
                hero_id: heroId
                # draft_type:
                draft_order: order
                # is_random:
                # by_steam_id:
                # extra data for parsing
                playerIndex
                isPick
                bannedHeroId
                wasBannedSuccessfully
              }
            }
          }
        }
        """
        MATCH_SPEC = {
            'match_id': 'id',
            'replay_salt': 'replaySalt',
            'patch_id': 'gameVersionId',
            'league_id': 'leagueId',
            'radiant_team_id': 'radiantTeamId',
            'dire_team_id': 'direTeamId',
            'start_datetime': 'startDateTime',
            'is_stats': 'isStats',
            'winning_faction': 'didRadiantWin',
            'duration': 'durationSeconds',
            'region': 'regionId',
            'lobby_type': 'lobbyType',
            'game_mode': 'gameMode',
            'tournament': TOURNAMENT_SPEC,
            'teams': [...],
            'draft': [...],
            'accounts': [...],
            'players': [...],
            'hero_movements': [...]
        }
        INCOMPLETE_MATCH_SPEC = {
            'match_id': 'id',
            'replay_salt': 'replaySalt'
        }
        resp = await self.query(q, match_ids=match_ids)
        spec = ('data.matches', [Or(MATCH_SPEC, INCOMPLETE_MATCH_SPEC)])
        matches = []

        for match in resp.json()['data']['matches']:
            m = {k: v for k, v in match.items() if not k.startswith('parse_')}

            try:
                m['tournament'] = match['parse_league']
                m['teams'] = parse_teams(match)
                m['draft'] = parse_draft(match)
                m['accounts'] = parse_accounts(match)
                m['players'] = parse_players(match)
                m['hero_movements'] = parse_hero_movements(match)
                m = Match(**m)
            except (TypeError, ValidationError):
                m = IncompleteMatch(match_id=m['match_id'], replay_salt=m['replay_salt'])

            matches.append(m)

        return matches

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
        spec = (
            'data.competitive_teams', [{
                'team_id': 'id',
                'team_name': 'name',
                'team_tag': 'tag',
                'created': 'dateCreated',
            }]
        )
        data = glom(resp.json(), spec)
        return [CompetitiveTeam(**v) for v in data]

    def __repr__(self) -> str:
        return f'<StratzClient {self.rate}r/s>'
