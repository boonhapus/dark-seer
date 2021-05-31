from typing import Optional
import datetime as dt

from pydantic import BaseModel, validator

from darkseer.models import (
    GameVersion as GameVersion_,
    Tournament as Tournament_
)


class Base(BaseModel):

    class Config:
        orm_mode = True

    def to_orm(cls):
        return cls.orm_model(**cls.dict())


class GameVersion(Base):
    patch_id: int
    patch: str
    release_dt: dt.datetime

    @property
    def orm_model(self):
        return GameVersion_

    @validator('release_dt', pre=True)
    def ensure_utc(cls, ts: int) -> dt.datetime:
        return dt.datetime.utcfromtimestamp(ts)


class Tournament(Base):
    league_id: int
    league_name: str
    league_start_date: Optional[dt.datetime]
    league_end_date: Optional[dt.datetime]
    tier: str
    prize_pool: int

    @property
    def orm_model(self):
        return Tournament_

    @validator('tier')
    def str_lower(cls, string: str) -> str:
        return f'{string}'.lower()

    @validator('league_start_date', 'league_end_date', pre=True)
    def ensure_utc(cls, ts: int) -> dt.datetime:
        if ts is None:
            return None

        return dt.datetime.utcfromtimestamp(ts)


class Hero(Base):
    hero_id: int
    hero_internal_name: str


class HeroHistory(Base):
    hero_id: int
    patch_id: int
    hero_internal_name: str
    hero_display_name: str
    primary_attribute: str
    mana_regen_base: float
    strength_base: float
    strength_gain: Optional[float]
    agility_base: float
    agility_gain: float
    intelligence_base: float
    intelligence_gain: float
    base_attack_time: float
    attack_range: int
    base_attack_time: float
    attack_type: str
    is_captains_mode: bool
    movespeed: int
    turn_rate: float
    armor_base: Optional[float]
    magic_armor_base: float
    damage_base_max: int
    damage_base_min: int
    is_radiant: bool
    vision_range_day: int
    vision_range_night: int

    @validator('is_radiant', pre=True)
    def flip_is_dire(cls, is_dire: bool) -> bool:
        return not is_dire

    @validator(
        'mana_regen_base', 'strength_base', 'strength_gain', 'agility_base',
        'agility_gain', 'intelligence_base', 'intelligence_gain', 'base_attack_time',
        'base_attack_time', 'turn_rate', 'armor_base', 'magic_armor_base',
        pre=True
    )
    def float_two_decimals(cls, value: float) -> float:
        if value is None:
            return None
        return float(f'{value:.2f}')

    def to_hero(self) -> Hero:
        """
        Convert this schema to a Hero.

        Useful for SCD4 activites.
        """
        return Hero(hero_id=self.hero_id, hero_internal_name=self.hero_internal_name)
