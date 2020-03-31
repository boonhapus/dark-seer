from datetime import datetime
from typing import Optional

from pydantic import validator, root_validator

from darkseer.schema import GameVersion, Match


class GameVersion(GameVersion):
    """
    Transformer for the STRATZ repr of a GameVersion.
    """
    @validator('release_date', pre=True)
    def as_utc(cls, v: int):
        """
        Enforce UTC timezone on all incoming timestamps.
        """
        return datetime.utcfromtimestamp(v)


class Match(Match):
    """
    Transformer for the STRATZ repr of a Match.
    """
    @root_validator(pre=True)
    def _prepare_stats(cls, data: dict) -> dict:
        data['draft'] = []

        # handle reformatting of MatchDraft
        for draft_item in data['stats']['draft']:

            if draft_item['is_pick']:
                hero_id = draft_item['picked_hero_id']
                draft_type = 'pick'
            else:
                hero_id = draft_item['banned_hero_id']
                draft_type = 'ban' if draft_item['banned'] else 'ban vote'

            try:
                steam_id = data['players'][draft_item['by_player_index']]['steam_id']
            except TypeError:
                steam_id = None

            data['draft'].append({
                'match_id': data['match_id'],
                'hero_id': hero_id,
                'draft_type': draft_type,
                'draft_order': draft_item['draft_order'],
                'by_steam_id': steam_id
            })

        return data
