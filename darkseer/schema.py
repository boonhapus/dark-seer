from datetime import date

from pydantic import BaseModel


class GameVersion(BaseModel):
    id: int
    patch: str
    release_date: date


class Hero(BaseModel):
    id: int
    # TODO ...
