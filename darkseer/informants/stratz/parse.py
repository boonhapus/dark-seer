from typing import Any, Optional, List, Dict

from glom import glom, S, T, Val, Invoke, Check, Flatten, SKIP
from rich import print


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


def classify_cs_target_event(npc_id: int) -> str:
    """
    Map a csEvent target npcId to a match_event type.
    """
    # Buildings
    if 16 < npc_id < 49:
        return 'building destroy'

    # Wards
    if npc_id == 110:
        return 'observer deward'

    if npc_id == 111:
        return 'sentry deward'

    # Couriers
    if npc_id in (112, 113):
        return 'courier snipe'

    if npc_id == 133:
        return 'roshan death'

    return 'creep kill'


def classify_ward_activity(ward_event: Dict) -> str:
    """
    """
    s = 'observer' if ward_event['wardType'] == 0 else 'sentry'
    s += ' plant' if ward_event['action'] == 0 else ' despawn'
    return s


def is_dewarded(player_events: Dict, spawn: int) -> bool:
    """
    """
    npc_id, max_secs = (110, 360) if spawn['type'] == 0 else (111, 480)
    despawn_time = 999

    for i, player in enumerate(player_events):
        for event in player['playbackData']['csEvents']:
            if (
                event['npcId'] == npc_id
                and event['time'] >= spawn['time']
                and event['positionX'] == spawn['positionX']
                and event['positionY'] == spawn['positionY']
            ):
                print(
                    'found a matching deward event!'
                    f'\n     spawn: {spawn}'
                    f'\n   despawn: {event}'
                    f'\n  duration: {event["time"] - spawn["time"]}'
                )
                despawn_time = event['time']

    # Difference between the two times. IF time is before the horn, it's negative, and
    # we're subtracting a negative number, which is just addition. Checks out.
    duration = despawn_time - spawn['time']

    return duration < max_secs


def ward_duration(ward_events: Dict, spawn: int, match_duration: int) -> int:
    """
    """
    return 999


def parse_events(m) -> Optional[FLAT_API_RESPONSE]:
    r = []

    # Ability Learn
    spec = (
        S(match_id='id'),
        'parse_player_events',
        [(
            S(hero_id='heroId'),
            'playbackData.abilityLearnEvents',
            [{
                'match_id': S.match_id,
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
        Flatten()
    )
    r.extend(glom(m, spec))

    # Ability Use
    spec = (
        S(match_id='id'),
        'parse_player_events',
        [(
            'playbackData.abilityUsedEvents',
            [{
                'match_id': S.match_id,
                'event_type': Val('ability use'),
                # 'id': ...,
                'time': 'time',
                'actor_id': 'attacker',
                'target_id': 'target',
                'ability_id': 'abilityId'
            }]
        )],
        Flatten()
    )
    r.extend(glom(m, spec))

    # Item Purchase
    spec = (
        S(match_id='id'),
        'parse_player_events',
        [(
            S(hero_id='heroId'),
            'stats.itemPurchases',
            [{
                'match_id': S.match_id,
                'event_type': Val('item purchase'),
                # 'id': ...,
                'time': 'time',
                'actor_id': S.hero_id,
                'item_id': 'itemId'
            }]
        )],
        Flatten()
    )
    r.extend(glom(m, spec))

    # Item Use
    spec = (
        S(match_id='id'),
        'parse_player_events',
        [(
            'playbackData.itemUsedEvents',
            [{
                'match_id': S.match_id,
                'event_type': Val('item use'),
                # 'id': ...,
                'time': 'time',
                'actor_id': 'attacker',
                'target_id': 'target',
                'item_id': 'itemId'
            }]
        )],
        Flatten()
    )
    r.extend(glom(m, spec))

    # Kill
    spec = (
        S(match_id='id'),
        'parse_player_events',
        [(
            S(hero_id='heroId'),
            'stats.killEvents',
            [{
                'match_id': S.match_id,
                'event_type': Val('hero kill'),
                # 'id': ...,
                'time': 'time',
                'x': 'positionX',
                'y': 'positionY',
                'actor_id': S.hero_id,
                'target_id': 'target',
                'ability_id': 'byAbility',
                'item_id': 'byItem',
            }]
        )],
        Flatten()
    )
    r.extend(glom(m, spec))

    # Death
    spec = (
        S(match_id='id'),
        'parse_player_events',
        [(
            S(hero_id='heroId'),
            'stats.deathEvents',
            [{
                'match_id': S.match_id,
                'event_type': Val('hero death'),
                # 'id': ...,
                'time': 'time',
                'x': 'positionX',
                'y': 'positionY',
                'actor_id': 'attacker',
                'target_id': S.hero_id,
                'ability_id': 'byAbility',
                'item_id': 'byItem',
                'extra_data': {
                    'gold_fed': 'goldFed',
                    'gold_lost': 'goldLost',
                }
            }]
        )],
        Flatten()
    )
    r.extend(glom(m, spec))

    # Assist
    spec = (
        S(match_id='id'),
        'parse_player_events',
        [(
            S(hero_id='heroId'),
            'stats.assistEvents',
            [{
                'match_id': S.match_id,
                'event_type': Val('hero assist'),
                # 'id': ...,
                'time': 'time',
                'x': 'positionX',
                'y': 'positionY',
                'actor_id': S.hero_id,
                'target_id': 'target',
            }]
        )],
        Flatten()
    )
    r.extend(glom(m, spec))

    # Creep Kill
    # Courier Snipe
    # Observer Deward
    # Sentry Deward
    # Roshan Death
    # Building Destroy
    spec = (
        S(match_id='id'),
        'parse_player_events',
        [(
            'playbackData.csEvents',
            [{
                'match_id': S.match_id,
                'event_type': Invoke(classify_cs_target_event).specs(T['npcId']),
                # 'id': ...,
                'time': 'time',
                'x': 'positionX',
                'y': 'positionY',
                'actor_id': 'attacker',
                'target_id': 'npcId',
                'ability_id': 'byAbility',
                'item_id': 'byItem'
            }]
        )],
        Flatten(),
        Invoke(sorted).specs(T).constants(key=lambda d: (d['event_type'], d['time'])),
        Invoke(enumerate).specs(T),
        [lambda e: {**e[1], 'id': e[0]}]
    )
    r.extend(glom(m, spec))

    # Creep Deny
    # these don't exist ;o

    # Gold Change
    # Experience Change

    # Buyback
    spec = (
        S(match_id='id'),
        'parse_player_events',
        [(
            'playbackData.buyBackEvents',
            [{
                'match_id': S.match_id,
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
        Flatten()
    )
    r.extend(glom(m, spec))

    # Observer Ward Planted
    # Sentry Ward Planted
    spec = (
        S(match_id='id'),
        S(match_duration='durationSeconds'),
        S(player_events='parse_player_events'),
        'parse_player_events',
        [(
            S(hero_id='heroId'),
            'stats.wards',
            [{
                'match_id': S.match_id,
                'event_type': Invoke(lambda x: 'observer plant' if x == 0 else 'sentry plant').specs(T['type']),
                # 'id': ...,
                'time': 'time',
                'actor_id': S.hero_id,
                'x': 'positionX',
                'y': 'positionY',
                # 'extra_data': {
                #     'is_dewarded': Invoke(is_dewarded).specs(S.player_events, spawn=T),
                #     'ward_duration': Invoke(ward_duration).specs(S.player_events, spawn=T, match_duration=S.match_duration)
                # }
            }]
        )],
        Flatten(),
    )
    r.extend(glom(m, spec))

    # print(glom(m, spec)[:5])
    # raise SystemExit(-1)

    # Rune Bottle
    # Rune Activate
    spec = (
        S(match_id='id'),
        'parse_player_events',
        [(
            S(hero_id='heroId'),
            'stats.runes',
            [{
                'match_id': S.match_id,
                'event_type': Invoke(lambda x: 'rune bottle' if 'BOTTLE' in x.lower() else 'rune activate').specs(T['action']),
                # 'id': ...,
                'time': 'time',
                'actor_id': S.hero_id,
                'x': 'positionX',
                'y': 'positionY',
                'extra_data': {
                    'rune': ('rune', str.lower),
                }
            }]
        )],
        Flatten()
    )
    r.extend(glom(m, spec))

    # Assign IDs all the way through each event type
    spec = (
        Invoke(sorted).specs(T).constants(key=lambda d: (d['event_type'], d['time'])),
        Invoke(enumerate).specs(T),
        [lambda e: {**e[1], 'id': e[0]}]
    )
    r = glom(r, spec)

    return r
