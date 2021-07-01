from typing import Any, Optional, List, Dict

from glom import glom, S, T, Val, SKIP, Invoke, Check, Match, Flatten


FLAT_API_RESPONSE = List[Dict[str, Any]]


def _parse_draft_type(pick_ban: List[Dict]) -> str:
    """
    One of.. ban vote, pick, ban
    """
    # TODO .. use glom?
    if pick_ban['isPick']:
        return 'pick'

    ban_type = 'ban'

    if pick_ban['playerIndex'] is None:
        ban_type = f'system generated {ban_type}'

    if not pick_ban['wasBannedSuccessfully']:
        ban_type = f'{ban_type} vote'

    return ban_type


def _parse_draft_is_random(
    players: List[Dict],
    *,
    player_idx: Optional[int]
) -> Optional[int]:
    # TODO .. use glom?
    if player_idx is None:
        return False

    return players[player_idx].get('isRandom')


def _parse_draft_actor(
    players: List[Dict],
    *,
    player_idx: Optional[int]
) -> Optional[int]:
    # TODO .. use glom?
    if player_idx is None:
        return None

    return players[player_idx].get('steamAccountId')


def is_a_creep(npc_id: int) -> bool:
    """
    """
    # Buildings
    if 16 < npc_id < 49:
        return False

    # Wards
    if npc_id in (110, 111):
        return False

    # Couriers
    if npc_id in (112, 113):
        return False

    # Yup, it's a creep.
    return True


def parse_events(m) -> Optional[FLAT_API_RESPONSE]:
    r = []

    match_id = Val(m['id'])
    player_data = m['parse_match_players']

    # Ability Learn
    spec = (
        'parse_player_events',
        [(
            S(hero_id='heroId'),
            'playbackData.abilityLearnEvents',
            [{
                'match_id': match_id,
                'event_type': Val('ability learn'),
                # 'id': ...,
                'time': 'time',
                'actor_id': S.hero_id,
                'ability_id': 'abilityId',
                'extra_data': {
                    'level': (T['level'], lambda x: x + 1),
                    'hero_level': 'levelObtained'
                }
            }]
        )],
        Flatten(),
        Invoke(sorted).specs(T).constants(key=lambda d: d['time']),
        Invoke(enumerate).specs(T),
        [lambda e: {**e[1], 'id': e[0]}]
    )
    r.extend(glom(m, spec))

    # Ability Use
    spec = (
        'parse_player_events',
        [(
            'playbackData.abilityUsedEvents',
            [{
                'match_id': match_id,
                'event_type': Val('ability use'),
                # 'id': ...,
                'time': 'time',
                'actor_id': 'attacker',
                'target_id': 'target',
                'ability_id': 'abilityId'
            }]
        )],
        Flatten(),
        Invoke(sorted).specs(T).constants(key=lambda d: d['time']),
        Invoke(enumerate).specs(T),
        [lambda e: {**e[1], 'id': e[0]}]
    )
    r.extend(glom(m, spec))

    # Item Purchase
    spec = (
        'parse_player_events',
        [(
            S(hero_id='heroId'),
            'playbackData.purchaseEvents',
            [{
                'match_id': match_id,
                'event_type': Val('item purchase'),
                # 'id': ...,
                'time': 'time',
                'actor_id': S.hero_id,
                'item_id': 'itemId'
            }]
        )],
        Flatten(),
        Invoke(sorted).specs(T).constants(key=lambda d: d['time']),
        Invoke(enumerate).specs(T),
        [lambda e: {**e[1], 'id': e[0]}]
    )
    r.extend(glom(m, spec))

    # Item Use
    spec = (
        'parse_player_events',
        [(
            'playbackData.itemUsedEvents',
            [{
                'match_id': match_id,
                'event_type': Val('item use'),
                # 'id': ...,
                'time': 'time',
                'actor_id': 'attacker',
                'target_id': 'target',
                'item_id': 'itemId'
            }]
        )],
        Flatten(),
        Invoke(sorted).specs(T).constants(key=lambda d: d['time']),
        Invoke(enumerate).specs(T),
        [lambda e: {**e[1], 'id': e[0]}]
    )
    r.extend(glom(m, spec))

    # Kill
    spec = (
        'parse_player_events',
        [(
            'playbackData.killEvents',
            [{
                'match_id': match_id,
                'event_type': Val('hero kill'),
                # 'id': ...,
                'time': 'time',
                'x': 'positionX',
                'y': 'positionY',
                'actor_id': 'attacker',
                'target_id': 'target',
                'ability_id': 'byAbility',
                'item_id': 'byItem',
                'extra_data': {
                    'is_from_illusion': 'isFromIllusion'
                }
            }]
        )],
        Flatten(),
        Invoke(sorted).specs(T).constants(key=lambda d: d['time']),
        Invoke(enumerate).specs(T),
        [lambda e: {**e[1], 'id': e[0]}]
    )
    r.extend(glom(m, spec))

    # Death
    spec = (
        'parse_player_events',
        [(
            'playbackData.deathEvents',
            [{
                'match_id': match_id,
                'event_type': Val('hero death'),
                # 'id': ...,
                'time': 'time',
                'x': 'positionX',
                'y': 'positionY',
                'actor_id': 'attacker',
                'target_id': 'target',
                'ability_id': 'byAbility',
                'item_id': 'byItem',
                'extra_data': {
                    'is_from_illusion': 'isFromIllusion',
                    'gold_fed': 'goldFed',
                    'gold_lost': 'goldLost',
                    'gold_reliable': 'reliableGold',
                    'gold_unreliable': 'unreliableGold'
                }
            }]
        )],
        Flatten(),
        Invoke(sorted).specs(T).constants(key=lambda d: d['time']),
        Invoke(enumerate).specs(T),
        [lambda e: {**e[1], 'id': e[0]}]
    )
    r.extend(glom(m, spec))

    # Assist
    spec = (
        'parse_player_events',
        [(
            'playbackData.assistEvents',
            [{
                'match_id': match_id,
                'event_type': Val('hero assist'),
                # 'id': ...,
                'time': 'time',
                'x': 'positionX',
                'y': 'positionY',
                'actor_id': 'attacker',
                'target_id': 'target',
            }]
        )],
        Flatten(),
        Invoke(sorted).specs(T).constants(key=lambda d: d['time']),
        Invoke(enumerate).specs(T),
        [lambda e: {**e[1], 'id': e[0]}]
    )
    r.extend(glom(m, spec))

    # Creep Kill
    spec = (
        'parse_player_events',
        [(
            'playbackData.csEvents',
            [(
                Check(T['npcId'], validate=is_a_creep, default=SKIP),
                {
                    'match_id': match_id,
                    'event_type': Val('creep kill'),
                    # 'id': ...,
                    'time': 'time',
                    'x': 'positionX',
                    'y': 'positionY',
                    'actor_id': 'attacker',
                    'target_id': 'npcId',
                    'ability_id': 'byAbility',
                    'item_id': 'byItem'
                }
            )]
        )],
        Flatten(),
        # Invoke(sorted).specs(T).constants(key=lambda d: d['time']),
        # Invoke(enumerate).specs(T),
        # [lambda e: {**e[1], 'id': e[0]}]
    )

    # Creep Deny
    # these don't exist ;o

    # Gold Change
    # Experience Change

    # Buyback
    spec = (
        'parse_player_events',
        [(
            'playbackData.buyBackEvents',
            [{
                'match_id': match_id,
                'event_type': Val('buyback'),
                # 'id': ...,
                'time': 'time',
                'actor_id': 'heroId',
                'extra_data': {
                    'death_timer_remaining_s': 'deathTimeRemaining',
                    'buyback_cost': 'cost'
                }
            }]
        )],
        Flatten(),
        Invoke(sorted).specs(T).constants(key=lambda d: d['time']),
        Invoke(enumerate).specs(T),
        [lambda e: {**e[1], 'id': e[0]}]
    )
    r.extend(glom(m, spec))

    # Courier Death
    # Look for CSEvents where NPC_ID = 112, 113

    # Observer Ward Placed
    # Sentry Ward Placed

    # Observer Ward Destroyed
    # Look for CSEvents where NPC_ID = 110

    # Sentry Ward Destroyed
    # Look for CSEvents where NPC_ID = 111

    # Roshan Death
    # Look for CSEvents where NPC_ID = 133

    # Building Death
    # Look for CSEvents where 16 < NPC_ID < 49

    # Rune Spawn
    # Rune Taken
    return r
