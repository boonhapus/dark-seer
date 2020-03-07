from datetime import datetime, date
from typing import List, Optional

from pydantic import BaseModel, validator

from darkseer.schema import GameVersion


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


class MatchSummary(BaseModel):
    """
    Basic information about a Match.
    """
    match_id: int
    league_id: int
    start_datetime: datetime
    parsed_datetime: Optional[datetime]
    duration: int
    lobby_type: int  # TODO: enum/validator
    game_mode: int  # TODO: enum/validator
    radiant_team_id: int  # TODO: enum/validator
    dire_team_id: int  # TODO: enum/validator
    is_radiant_win: bool


class LeagueSummary(BaseModel):
    """
    Basic information about a League.
    """
    league_id: int
    league_name: str
    league_start_date: date
    league_end_date: date
    match_summaries: List[MatchSummary]
