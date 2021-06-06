from typing import List

import httpx

from darkseer.util import RateLimitedHTTPClient, FileCache, chunks
from .schema import (
    GameVersion, Tournament, CompetitiveTeam, Match,
    HeroHistory, ItemHistory, NPCHistory, AbilityHistory
)
from .parse import _parse_draft_type, _parse_draft_is_random, _parse_draft_actor


_cache = FileCache('C:/projects/dark-seer/scripts/cache')


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
        super().__init__(tokens=300, seconds=3600, base_url='https://api.stratz.com', timeout=None)

        if bearer_token is not None:
            self.tokens = 500
            self.headers.update({'authorization': f'Bearer {bearer_token}'})

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
            game_version: gameVersions {
              patch_id: id
              patch: name
              release_datetime: asOfDateTime
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

    async def tournament_matches(self, *, league_id: int) -> List[Match]:
        """
        """
        q = """
        query TournamentMatches {
          tournament_matches: league(id: $league_id) {
            league_name: displayName
            matches(request: {
              skip: $skip_value,
              take: 50,
              isParsed: true
            }) {
              match_id: id
            }
          }
        }
        """
        matches = []
        _match_ids = []

        # Get all Match IDs for all tournaments.
        while True:
            skip = len(_match_ids)
            resp = await self.query(q, league_id=league_id, skip_value=skip)
            data = resp.json()['data']

            for v in data['tournament_matches']['matches']:
                if v['match_id'] not in _match_ids:
                    _match_ids.append(v['match_id'])

            if not data['tournament_matches']['matches']:
                break

        # Get all matches
        for chunk in chunks(_match_ids, n=10):
            r = await self.matches(match_ids=chunk)
            matches.extend(r)

        return matches

    async def matches(self, *, match_ids: List[int]) -> List[Match]:
        """
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
            match_id: id
            patch_id: gameVersionId
            league_id: leagueId
            radiant_team_id: radiantTeamId
            dire_team_id: direTeamId
            start_datetime: startDateTime
            is_stats: isStats
            winning_faction: didRadiantWin
            duration: durationSeconds
            region: regionId
            lobby_type: lobbyType
            game_mode: gameMode

            parse_datetime: parsedDateTime
            parse_league: league {
              league_id: id
              league_name: displayName
              league_start_date: startDateTime
              league_end_date: endDateTime
              tier
              prize_pool: prizePool
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
        resp = await self.query(q, match_ids=match_ids)
        matches = []

        for m in resp.json()['data']['matches']:
            if m['parse_datetime'] is None:
                continue

            m['tournament'] = m['parse_league']

            m['teams'] = [
                t
                for t in (m['parse_radiant'], m['parse_dire'])
                if t is not None
            ]

            m['draft'] = [
                {
                    'match_id': m['match_id'],
                    'hero_id': pick_ban['hero_id'] or pick_ban['bannedHeroId'],
                    'draft_type': _parse_draft_type(pick_ban),
                    'draft_order': pick_ban['draft_order'],
                    'is_random': _parse_draft_is_random(m['parse_match_players'], player_idx=pick_ban['playerIndex']),
                    'by_steam_id': _parse_draft_actor(m['parse_match_players'], player_idx=pick_ban['playerIndex'])
                }
                for pick_ban in m['parse_match_draft']['pick_bans']
            ]

            m['accounts'] = [
                {
                    'steam_id': p['acct']['steam_id'],
                    'steam_name': p['acct']['is_pro']['steam_name'] if p['acct']['is_pro'] else p['acct']['steam_name']
                }
                for p in m['parse_match_players']
            ]

            m['players'] = [
                {
                    'match_id': m['match_id'],
                    **{k: v for k, v in p.items() if k != 'isRandom'}
                }
                for p in m['parse_match_players']
            ]

            m['hero_movements'] = [
                {
                    'match_id': m['match_id'],
                    'hero_id': player['hero_id'],
                    'id': i,
                    **position
                }
                for player in m['parse_match_players']
                for i, position in enumerate(player['hero_movement']['positions'])
            ]

            # remove extra data
            [m.pop(k) for k in list(m.keys()) if k.startswith('parse_')]
            matches.append(Match(**m))

        return matches

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
                faction: team
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

    async def items(self, *, patch_id: int=69) -> List[ItemHistory]:
        """
        Return a list of Items.
        """
        q = """
        query Items {
          constants {
            items (gameVersionId: $patch_id, language: ENGLISH) {
              item_id: id
              item_internal_name: shortName
              item_display_name: displayName
              stat {
                cost
                is_recipe: isRecipe
                is_side_shop: isSideShop
                quality
                unit_target_flags: unitTargetFlags
                unit_target_team: unitTargetTeam
                unit_target_type: unitTargetType
              }
            }
          }
        }
        """
        resp = await self.query(q, patch_id=patch_id)
        items = []

        for item in resp.json()['data']['constants']['items']:
            if item['stat'] is None:
                continue

            data = {'patch_id': patch_id, **item, **item['stat']}
            data.pop('stat')
            items.append(data)

        return [ItemHistory(**v) for v in items]

    async def npcs(self, *, patch_id=69) -> List[NPCHistory]:
        """
        Return a list of NPCs.
        """
        q = """
        query NPCs {
          constants {
            npcs (gameVersionId: $patch_id) {
              npc_id: id
              npc_internal_name: name
              stat {
                combat_class_attack: combatClassAttack
                combat_class_defend: combatClassDefend
                is_ancient: isAncient
                is_neutral: isNeutralUnitType
                health: statusHealth
                mana: statusMana
                faction: teamName
                unit_relationship_class: unitRelationshipClass
              }
            }
          }
        }
        """
        resp = await self.query(q, patch_id=patch_id)
        npcs = []

        for npc in resp.json()['data']['constants']['npcs']:
            if npc['stat'] is None:
                continue

            data = {'patch_id': patch_id, **npc, **npc['stat']}
            data.pop('stat')
            npcs.append(data)

        return [NPCHistory(**v) for v in npcs]

    async def abilities(self, *, patch_id=69) -> List[AbilityHistory]:
        """
        Return a list of Abilities.
        """
        q = """
        query Abilities {
          constants {
            abilities (gameVersionId: $patch_id, language: ENGLISH) {
              ability_id: id
              ability_internal_name: name
              is_talent: isTalent
              language {
                ability_display_name: displayName
              }
              stat {
                has_scepter_upgrade: hasScepterUpgrade
                is_scepter_upgrade: isGrantedByScepter
                is_aghanims_shard: isGrantedByShard
                is_ultimate: isUltimate
                required_level: requiredLevel
                ability_type: type
                ability_damage_type: unitDamageType
                unit_target_flags: unitTargetFlags
                unit_target_team: unitTargetTeam
                unit_target_type: unitTargetType
              }
            }
          }
        }
        """
        resp = await self.query(q, patch_id=patch_id)
        abilities = []

        for ability in resp.json()['data']['constants']['abilities']:
            if ability['stat'] is None:
                continue
            if ability['ability_internal_name'] is None:
                continue

            data = {'patch_id': patch_id, **ability, **ability['stat']}

            if ability['language'] is not None:
                data = {**data, **ability['language']}

            data.pop('language')
            data.pop('stat')
            abilities.append(data)

        return [AbilityHistory(**v) for v in abilities]

    def __repr__(self) -> str:
        return f'<StratzClient {self.rate}r/s>'
