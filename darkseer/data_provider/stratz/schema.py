from datetime import datetime

from pydantic import validator

from darkseer.schema import GameVersion


class GameVersion(GameVersion):

    @validator('release_date', pre=True)
    def as_utc(cls, v: int):
        """
        Enforce UTC timezone on all incoming timestamps.
        """
        return datetime.utcfromtimestamp(v)
