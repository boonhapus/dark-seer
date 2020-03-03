from datetime import date

from pydantic import BaseModel, HttpUrl


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
    cdn_img_url: HttpUrl
    league_start_date: date
    league_end_date: date
