from typing import Optional
import datetime as dt

from pydantic import BaseModel, validator

from darkseer.models import GameVersion as GameVersion_


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

    @validator('tier')
    def str_lower(cls, string: str) -> str:
        return f'{string}'.lower()

    @validator('league_start_date', 'league_end_date', pre=True)
    def ensure_utc(cls, ts: int) -> dt.datetime:
        if ts is None:
            return None

        return dt.datetime.utcfromtimestamp(ts)


class CompetitiveTeam(Base):
    team_id: int
    team_name: str
    team_tag: str
    country_code: str
    created: dt.datetime

    @validator('created', pre=True)
    def ensure_utc(cls, ts: int) -> dt.datetime:
        if ts is None:
            return None

        return dt.datetime.utcfromtimestamp(ts)


class Match(Base):
    """
    """


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


class Item(Base):
    item_id: int
    item_internal_name: str


class ItemHistory(Base):
    item_id: int
    patch_id: int
    item_internal_name: str
    item_display_name: str
    cost: Optional[int]
    is_recipe: bool
    is_side_shop: bool
    quality: Optional[str]
    unit_target_flags: Optional[int]
    unit_target_team: Optional[int]
    unit_target_type: Optional[int]

    def to_item(self) -> Item:
        """
        Convert this schema to an Item.

        Useful for SCD4 activites.
        """
        return Item(item_id=self.item_id, item_internal_name=self.item_internal_name)


class NPC(Base):
    npc_id: int
    npc_internal_name: str


class NPCHistory(Base):
    npc_id: int
    patch_id: int
    npc_internal_name: str
    combat_class_attack: str
    combat_class_defend: str
    is_ancient: bool
    is_neutral: bool
    health: int
    mana: int
    team: str
    unit_relationship_class: str

    @validator('team', pre=True)
    def translate_team(cls, value: str) -> str:
        mapping = {'goodguys': 'radiant', 'badguys': 'dire', 'neutrals': 'neutral'}
        return mapping.get(value.lower())

    def to_npc(self) -> Item:
        """
        Convert this schema to an NPC.

        Useful for SCD4 activites.
        """
        return NPC(npc_id=self.npc_id, npc_internal_name=self.npc_internal_name)


class Ability(Base):
    ability_id: int
    ability_internal_name: str


class AbilityHistory(Base):
    ability_id: int
    patch_id: int
    ability_internal_name: str
    ability_display_name: Optional[str]
    is_talent: bool
    is_ultimate: bool
    has_scepter_upgrade: Optional[bool]
    is_scepter_upgrade: Optional[bool]
    is_aghanims_shard: Optional[bool]
    required_level: Optional[int]
    ability_type: Optional[int]
    ability_damage_type: Optional[int]
    unit_target_flags: Optional[int]
    unit_target_team: Optional[int]
    unit_target_type: Optional[int]

    def to_ability(self) -> Item:
        """
        Convert this schema to an NPC.

        Useful for SCD4 activites.
        """
        return Ability(ability_id=self.ability_id, ability_internal_name=self.ability_internal_name)
