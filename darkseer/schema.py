from datetime import date

from pydantic import BaseModel


class GameVersion(BaseModel):
    patch_id: int
    patch: str
    release_date: date


class Hero(BaseModel):
    hero_id: int
    ...
