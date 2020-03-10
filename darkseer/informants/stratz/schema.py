from datetime import datetime
from typing import Optional

from pydantic import validator

from darkseer.schema import EnumeratedModel, GameVersion


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


# class MatchSummary(EnumeratedModel):
#     """
#     Basic information about a Match.
#     """
#     match_id: int
#     league_id: int
#     start_datetime: datetime
#     parsed_datetime: Optional[datetime]
#     duration: int
#     region: str
#     lobby_type: str
#     game_mode: str
#     radiant_team_id: int
#     dire_team_id: int
#     is_radiant_win: bool
