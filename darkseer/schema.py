from datetime import date
from typing import Optional, List

from pydantic import BaseModel, validator


class EnumeratedModel(BaseModel):
    """
    A BaseModel to handle consistent enumerated fields.

    Certain fields are enumerated to conserve data volumes. This is
    useful across millions of matches, but it's unlikely DarkSeer will
    ever be tasked to handle this.
    """
    @validator('region', pre=True, check_fields=False)
    def _region_id_to_name(cls, v: int) -> str:
        REGIONS = {
            0: 'UNDEFINED', 1: 'US West', 2: 'US East', 3: 'Europe West',
            5: 'SE Asia', 6: 'Dubai', 7: 'Australia', 8: 'Stockholm',
            9: 'Austria', 10: 'Brazil', 11: 'South Africa', 12: 'China',
            13: 'China', 14: 'Chile', 15: 'Peru', 16: 'India', 17: 'China',
            18: 'China', 19: 'Japan', 20: 'China', 25: 'China', 37: 'Taiwan'
        }
        return REGIONS[v]

    @validator('lobby_type', pre=True, check_fields=False)
    def _lobby_id_to_name(cls, v: int) -> str:
        LOBBY_TYPES = {
            0: 'Normal', 1: 'Practice', 2: 'Tournament', 3: 'Tutorial',
            4: 'Co-op Bots', 5: 'Team Matchmaking', 6: 'Solo Matchmaking',
            7: 'Ranked', 8: '1v1 Mid', 9: 'Battle Cup'
        }
        return LOBBY_TYPES[v]

    @validator('game_mode', pre=True, check_fields=False)
    def _game_mode_to_name(cls, v: int) -> str:
        GAME_MODES = {
            0: 'Unknown', 1: 'All Pick', 2: 'Captains Mode', 3: 'Random Draft',
            4: 'Single Draft', 5: 'All Random', 12: 'Least Played',
            16: 'Captains Draft', 17: 'Balanced Draft', 22: 'All Draft'
        }
        return GAME_MODES[v]


class GameVersion(BaseModel):
    patch_id: int
    patch: str
    release_date: date


class Hero(BaseModel):
    hero_id: int
    ...


class Item(BaseModel):
    ...


class Tournament(BaseModel):
    league_id: int
    league_name: str
    league_start_date: date
    league_end_date: date
    prize_pool: Optional[int]
    match_ids: List[int]


class Match(EnumeratedModel):
    ...
