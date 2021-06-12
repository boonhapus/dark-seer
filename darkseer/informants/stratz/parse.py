from typing import Any, Optional, List, Dict


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

    return players[player_idx].get('steam_id')


def parse_draft(m) -> Optional[FLAT_API_RESPONSE]:
    # TODO .. use glom?
    r = [
        {
            'match_id': m['id'],
            'hero_id': pick_ban['heroId'] or pick_ban['bannedHeroId'],
            'draft_type': _parse_draft_type(pick_ban),
            'draft_order': pick_ban['order'],
            'is_random': _parse_draft_is_random(m['parse_match_players'], player_idx=pick_ban['playerIndex']),
            'by_steam_id': _parse_draft_actor(m['parse_match_players'], player_idx=pick_ban['playerIndex'])
        }
        for pick_ban in m['parse_match_draft']['pick_bans']
    ]
    return r
