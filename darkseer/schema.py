"""
Schema exist for the sole purpose of validating and sanitizing INCOMING
data into Dark Seer. The base darkseer.schema demonstrates the final
form the data will be in before going into the database. Any informants
who process data shall inherit from and validate/transform data before
it reaches these schema.
"""
from datetime import date, datetime
from typing import Optional, List

from pydantic import BaseModel, validator


class GameVersion(BaseModel):
    __schema_name__ = 'GameVersion'
    patch_id: int
    patch: str
    release_date: date

    def __str__(self):
        date = self.release_date.strftime('%Y-%m-%d')
        return f'<[s] GameVersion [{date}] patch {self.patch: <5}>'


class Hero(BaseModel):
    __schema_name__ = 'Hero'
    hero_id: int
    ...

    def __str__(self):
        return f'<[s] Hero: [{self.hero_id}] {self.display_name}>'


class Item(BaseModel):
    __schema_name__ = 'Item'
    ...

    def __str__(self):
        return f'<[s] Item: [{self.item_id}] {self.display_name}>'


class Tournament(BaseModel):
    __schema_name__ = 'Tournament'
    league_id: int
    league_name: str
    league_start_date: date
    league_end_date: date
    prize_pool: Optional[int]
    match_ids: List[int]

    def __str__(self):
        name = self.league_name
        date = self.league_start_date.strftime('%Y-%m-%d')
        prize = self.prize_pool
        n_matches = len(self.match_ids)
        return f'<[s] Tournament: [{date}] {name} ({n_matches} matches) ${prize:,}>'


class MatchDraft(BaseModel):
    __schema_name__ = 'MatchDraft'
    match_id: int
    hero_id: int
    draft_type: str
    draft_order: Optional[int]
    by_steam_id: Optional[int]

    def __str__(self):
        type_ = self.draft_type
        no = f' #{self.draft_order}' if self.draft_order is not None else ''
        return f'<[s] Draft: {type_}{no} for hero={self.hero_id}>'


class Match(BaseModel):
    __schema_name__ = 'Match'
    match_id: int
    region: str
    lobby_type: str
    game_mode: str
    patch_id: int
    start_datetime: datetime
    duration: int
    is_radiant_win: bool
    is_stats: bool
    league_id: Optional[int]
    series_id: Optional[int]
    radiant_team_id: Optional[int]
    dire_team_id: Optional[int]
    rank: int
    draft: List[MatchDraft]
    # players: List[MatchPlayer]
    # events: List[MatchEvent]

    @validator('region', pre=True)
    def _region_id_to_name(cls, v: int) -> str:
        REGIONS = {
            0: 'UNDEFINED', 1: 'US West', 2: 'US East',        3: 'Europe West',
            5: 'SE Asia',   6: 'Dubai',   7: 'Australia',      8: 'Stockholm',
            9: 'Austria',  10: 'Brazil', 11: 'South Africa',  12: 'China',
            13: 'China',   14: 'Chile',  15: 'Peru',          16: 'India',
            17: 'China',   18: 'China',  19: 'Japan',         20: 'China',
            25: 'China',   37: 'Taiwan'
        }
        return REGIONS[v]

    @validator('lobby_type', pre=True)
    def _lobby_id_to_name(cls, v: int) -> str:
        LOBBY_TYPES = {
            0: 'Normal',           1: 'Practice',   2: 'Tournament',
            3: 'Tutorial',         4: 'Co-op Bots', 5: 'Team Matchmaking',
            6: 'Solo Matchmaking', 7: 'Ranked',     8: '1v1 Mid',
            9: 'Battle Cup'
        }
        return LOBBY_TYPES[v]

    @validator('game_mode', pre=True)
    def _game_mode_to_name(cls, v: int) -> str:
        GAME_MODES = {
            0: 'Unknown',       1: 'All Pick',         2: 'Captains Mode',
            3: 'Random Draft',  4: 'Single Draft',     5: 'All Random',
            12: 'Least Played', 16: 'Captains Draft', 17: 'Balanced Draft',
            22: 'All Draft'
        }
        return GAME_MODES[v]

    def __str__(self):
        ranked = 'Ranked' if self.is_stats else 'Unranked'
        dt = self.start_datetime.strftime('%Y-%m-%d %H:%M:%S %Z')
        winner = 'Radiant' if self.is_radiant_win else 'Dire'
        return f'<[s] {ranked}Match: [{dt}] {self.match_id} - Winner: {winner}>'
