from typing import Any, Optional, List, Dict

from glom import glom, T, Val, Invoke, Flatten


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


def parse_events(m) -> Optional[FLAT_API_RESPONSE]:
    r = []

    match_id = Val(m['id'])
    player_data = m['parse_match_players']

    # Ability Learn
    # parse_player_events.playbackData.abilityLearnEvents

    # Ability Use
    # parse_player_events.playbackData.abilityUsedEvents

    # Item Purchase
    # parse_player_events.playbackData.purchaseEvents

    # Item Use
    # parse_player_events.playbackData.itemUsedEvents

    # Kill
    spec = (
        'parse_player_events',
        [(
            'playbackData.killEvents',
            [{
                'match_id': match_id,
                'event_type': Val('hero_kill'),
                # 'id': ...,
                'time': 'time',
                'x': 'positionX',
                'y': 'positionY',
                'ability_id': 'byAbility',
                'item_id': 'byItem',
                'actor_id': 'attacker',
                'target_id': 'target',
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
                'event_type': Val('hero_death'),
                # 'id': ...,
                'time': 'time',
                'x': 'positionX',
                'y': 'positionY',
                'ability_id': 'byAbility',
                'item_id': 'byItem',
                'actor_id': 'attacker',
                'target_id': 'target',
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
                'event_type': Val('hero_assist'),
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
    # parse_player_events.playbackData.csEvents

    # Creep Deny

    # Gold Change
    # Experience Change

    # Buyback
    # parse_player_events.playbakData.buyBackEvents

    # Courier Death
    # Ward Placed
    # Ward Destroyed
    # Roshan Death
    # Building Death
    # Rune Spawn
    # Rune Taken
    return r
