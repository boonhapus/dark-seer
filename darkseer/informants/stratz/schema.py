from typing import Optional, List
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
    release_datetime: dt.datetime

    @property
    def orm_model(self):
        return GameVersion_

    @validator('release_datetime', pre=True)
    def ensure_utc(cls, ts: int) -> dt.datetime:
        return dt.datetime.utcfromtimestamp(ts)


class Account(Base):
    steam_id: int
    steam_name: str
    discord_id: Optional[int]


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
    country_code: Optional[str]
    created: Optional[dt.datetime]

    @validator('created', pre=True)
    def ensure_utc(cls, ts: int) -> dt.datetime:
        if ts is None:
            return None

        return dt.datetime.utcfromtimestamp(ts)


class MatchPlayer(Base):
    match_id: int
    hero_id: int
    steam_id: int
    slot: int
    party_id: Optional[int]
    is_leaver: bool


class HeroMovement(Base):
    match_id: int
    hero_id: int
    id: int
    time: int
    x: int
    y: int


class MatchDraft(Base):
    match_id: int
    hero_id: int
    draft_type: str
    draft_order: Optional[int]
    is_random: bool
    by_steam_id: Optional[int]


class Match(Base):
    match_id: int
    patch_id: int
    league_id: Optional[int]
    series_id: Optional[int]
    radiant_team_id: Optional[int]
    dire_team_id: Optional[int]
    start_datetime: dt.datetime
    winning_faction: str
    is_stats: bool
    duration: int
    region: str
    lobby_type: str
    game_mode: str

    tournament: Optional[Tournament]
    teams: Optional[List[CompetitiveTeam]]
    accounts: Optional[List[Account]]
    draft: List[MatchDraft]
    players: List[MatchPlayer]
    hero_movements: List[HeroMovement]
    # events: List[MatchEvent]

    @validator('start_datetime', pre=True)
    def ensure_utc(cls, ts: int) -> dt.datetime:
        if ts is None:
            return None

        return dt.datetime.utcfromtimestamp(ts)

    @validator('winning_faction', pre=True)
    def parse_winner(cls, is_radiant_win: bool) -> str:
        return 'radiant' if is_radiant_win else 'dire'

    @validator('region', pre=True)
    def region_id_to_name(cls, region_id: int) -> str:
        regions = {
            0: 'UNDEFINED', 1: 'US West', 2: 'US East',        3: 'Europe West',
            5: 'SE Asia',   6: 'Dubai',   7: 'Australia',      8: 'Stockholm',
            9: 'Austria',  10: 'Brazil', 11: 'South Africa',  12: 'China',
            13: 'China',   14: 'Chile',  15: 'Peru',          16: 'India',
            17: 'China',   18: 'China',  19: 'Japan',         20: 'China',
            25: 'China',   37: 'Taiwan'
        }
        return regions[region_id]

    @validator('lobby_type', pre=True)
    def lobby_id_to_name(cls, lobby_id: int) -> str:
        lobby_types = {
            0: 'Normal',           1: 'Practice',   2: 'Tournament',
            3: 'Tutorial',         4: 'Co-op Bots', 5: 'Team Matchmaking',
            6: 'Solo Matchmaking', 7: 'Ranked',     8: '1v1 Mid',
            9: 'Battle Cup'
        }
        return lobby_types[lobby_id]

    @validator('game_mode', pre=True)
    def game_mode_to_name(cls, game_mode_id: int) -> str:
        game_modes = {
            0: 'Unknown',       1: 'All Pick',         2: 'Captains Mode',
            3: 'Random Draft',  4: 'Single Draft',     5: 'All Random',
            12: 'Least Played', 16: 'Captains Draft', 17: 'Balanced Draft',
            22: 'All Draft'
        }
        return game_modes[game_mode_id]


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
    faction: str
    vision_range_day: int
    vision_range_night: int

    @validator('faction', pre=True)
    def determine_team(cls, is_dire: bool) -> bool:
        return 'dire' if is_dire else 'radiant'

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
    faction: str
    unit_relationship_class: str

    @validator('faction', pre=True)
    def translate_faction(cls, value: str) -> str:
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
