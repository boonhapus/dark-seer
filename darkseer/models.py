from sqlalchemy import (
    Column, ForeignKey,
    Date, DateTime, SmallInteger, Integer, BigInteger, Float, Boolean, String
)
from sqlalchemy.dialects.postgresql import JSON

from darkseer.database import Base


class Account(Base):
    __tablename__ = 'account'

    steam_id = Column(BigInteger, primary_key=True)
    steam_name = Column(String)
    discord_id = Column(BigInteger, nullable=True)

    def __str__(self):
        name = self.steam_name
        return f'<[m] Account name={name}>'


class CompetitiveTeam(Base):
    __tablename__ = 'competitive_team'

    team_id = Column(BigInteger, primary_key=True)
    team_name = Column(String)
    team_tag = Column(String)
    country_code = Column(String, comment='this field is poorly maintained')
    created = Column(Date)

    def __str__(self):
        name = self.team_name
        return f'<[m] CompetitiveTeam name={name}>'


class Tournament(Base):
    __tablename__ = 'tournament'

    league_id = Column(BigInteger, primary_key=True)
    league_name = Column(String)
    league_start_date = Column(Date, comment='held as naive, but UTC')
    league_end_date = Column(Date, comment='held as naive, but UTC')
    tier = Column(String, comment='dpc, minor, major, international')
    prize_pool = Column(BigInteger)

    def __str__(self):
        name = self.league_name
        date = self.league_start_date.strftime('%Y-%m-%d')
        prize = self.prize_pool
        n_matches = len(self.matches)
        return f'<[m] Tournament: [{date}] {name} ({n_matches} matches) ${prize:,}>'


class GameVersion(Base):
    __tablename__ = 'game_version'

    patch_id = Column(Integer, primary_key=True)
    patch = Column(String)
    release_datetime = Column(DateTime)

    def __str__(self):
        patch = self.patch
        return f'<[m] GameVersion patch={patch}>'


class Hero(Base):
    __tablename__ = 'hero'

    hero_id = Column(SmallInteger, primary_key=True)
    hero_internal_name = Column(String)

    def __str__(self):
        name = self.display_name
        return f'<[m] Hero {name}>'


class HeroHistory(Base):
    __tablename__ = 'hero_history'

    hero_id = Column(SmallInteger, ForeignKey('hero.hero_id'), primary_key=True)
    patch_id = Column(Integer, ForeignKey('game_version.patch_id'), primary_key=True)
    hero_internal_name = Column(String)
    hero_display_name = Column(String)
    primary_attribute = Column(String)
    mana_regen_base = Column(Float)
    strength_base = Column(Float)
    strength_gain = Column(Float)
    agility_base = Column(Float)
    agility_gain = Column(Float)
    intelligence_base = Column(Float)
    intelligence_gain = Column(Float)
    base_attack_time = Column(Float)
    attack_range = Column(Integer)
    base_attack_time = Column(Float)
    attack_type = Column(String)
    is_captains_mode = Column(Boolean)
    movespeed = Column(Integer)
    turn_rate = Column(Float)
    armor_base = Column(Float)
    magic_armor_base = Column(Float)
    damage_base_max = Column(Integer)
    damage_base_min = Column(Integer)
    faction = Column(String)
    vision_range_day = Column(Integer)
    vision_range_night = Column(Integer)

    def __str__(self):
        name = self.display_name
        patch = self.game_version.patch
        return f'<[m] Hero {name} ({patch})>'


class NPC(Base):
    __tablename__ = 'non_player_character'

    npc_id = Column(Integer, primary_key=True)
    npc_internal_name = Column(String)

    def __str__(self):
        name = self.npc_name
        return f'<[m] NPC {name}>'


class NPCHistory(Base):
    __tablename__ = 'non_player_character_history'

    npc_id = Column(Integer, ForeignKey('non_player_character.npc_id'), primary_key=True)
    patch_id = Column(Integer, ForeignKey('game_version.patch_id'), primary_key=True)
    npc_internal_name = Column(String)
    combat_class_attack = Column(String)
    combat_class_defend = Column(String)
    is_ancient = Column(Boolean)
    is_neutral = Column(Boolean)
    health = Column(Integer)
    mana = Column(Integer)
    faction = Column(String)
    unit_relationship_class = Column(String)

    def __str__(self):
        name = self.npc.npc_name
        patch = self.game_version.patch
        return f'<[m] NPC {name} ({patch})>'


class Item(Base):
    __tablename__ = 'item'

    item_id = Column(Integer, primary_key=True)
    item_internal_name = Column(String)

    def __str__(self):
        name = self.item_internal_name
        return f'<[m] Item {name}>'


class ItemHistory(Base):
    __tablename__ = 'item_history'

    item_id = Column(Integer, ForeignKey('item.item_id'), primary_key=True)
    patch_id = Column(Integer, ForeignKey('game_version.patch_id'), primary_key=True)
    item_internal_name = Column(String)
    item_display_name = Column(String)
    cost = Column(Integer)
    is_recipe = Column(Boolean)
    is_side_shop = Column(Boolean)
    quality = Column(String, nullable=True)
    unit_target_flags = Column(Integer, nullable=True)
    unit_target_team = Column(Integer, nullable=True)
    unit_target_type = Column(Integer, nullable=True)

    def __str__(self):
        name = self.display_name
        patch = self.game_version.patch
        return f'<[m] NPC {name} ({patch})>'


class Ability(Base):
    __tablename__ = 'ability'

    ability_id = Column(Integer, primary_key=True)
    ability_internal_name = Column(String)

    def __str__(self):
        name = self.ability_internal_name
        return f'<[m] Ability {name}>'


class AbilityHistory(Base):
    __tablename__ = 'ability_history'

    ability_id = Column(Integer, ForeignKey('ability.ability_id'), primary_key=True)
    patch_id = Column(Integer, ForeignKey('game_version.patch_id'), primary_key=True)
    ability_internal_name = Column(String)
    ability_display_name = Column(String)
    is_talent = Column(Boolean)
    has_scepter_upgrade = Column(Boolean)
    is_scepter_upgrade = Column(Boolean)
    is_aghanims_shard = Column(Boolean)
    is_ultimate = Column(Boolean)
    required_level = Column(Integer)
    ability_type = Column(Integer)
    ability_damage_type = Column(Integer)
    unit_target_flags = Column(Integer)
    unit_target_team = Column(Integer)
    unit_target_type = Column(Integer)

    def __str__(self):
        name = self.ability.ability_internal_name
        patch = self.game_version.patch
        return f'<[m] Ability {name} ({patch})>'


class Match(Base):
    __tablename__ = 'match'

    match_id = Column(BigInteger, primary_key=True)
    replay_salt = Column(BigInteger)
    patch_id = Column(Integer, ForeignKey('game_version.patch_id'))
    league_id = Column(BigInteger, ForeignKey('tournament.league_id'), nullable=True)
    series_id = Column(BigInteger, nullable=True)
    radiant_team_id = Column(BigInteger, ForeignKey('competitive_team.team_id'), nullable=True)
    dire_team_id = Column(BigInteger, ForeignKey('competitive_team.team_id'), nullable=True)
    start_datetime = Column(DateTime, comment='held as naive, but UTC')
    is_stats = Column(Boolean)
    winning_faction = Column(String)
    duration = Column(Integer, comment='held as seconds')
    region = Column(String)
    lobby_type = Column(String)
    game_mode = Column(String)

    def __str__(self):
        ranked = 'Ranked' if self.is_stats else 'Unranked'
        dt = self.start_datetime.strftime('%Y-%m-%d %H:%M:%S %Z')
        id = self.match_id
        winner = 'Radiant' if self.is_radiant_win else 'Dire'
        return f'<[m] {ranked}Match: [{dt}] {id} - Winner: {winner}>'


class MatchPlayer(Base):
    __tablename__ = 'match_player'

    match_id = Column(BigInteger, ForeignKey('match.match_id'), primary_key=True)
    hero_id = Column(SmallInteger, ForeignKey('hero.hero_id'), primary_key=True)
    steam_id = Column(BigInteger, ForeignKey('account.steam_id'), nullable=True)
    slot = Column(Integer)
    party_id = Column(Integer)
    is_leaver = Column(Boolean)

    def __str__(self):
        hero_name = self.hero.display_name
        return f'<[m] Player: slot {self.slot} on {hero_name}>'


class MatchHeroMovement(Base):
    __tablename__ = 'match_hero_movement'

    match_id = Column(BigInteger, ForeignKey('match.match_id'), primary_key=True)
    hero_id = Column(SmallInteger, ForeignKey('hero.hero_id'), primary_key=True)
    id = Column(Integer, primary_key=True)
    time = Column(SmallInteger)
    x = Column(SmallInteger)
    y = Column(SmallInteger)

    def __str__(self):
        hero = self.hero.display_name
        time = self.time
        x = self.x
        y = self.y
        return f'<[m] Movement of {hero} @ {time} loc: ({x}, {y})>'


class MatchDraft(Base):
    __tablename__ = 'match_draft'

    match_id = Column(BigInteger, ForeignKey('match.match_id'), primary_key=True)
    hero_id = Column(SmallInteger, ForeignKey('hero.hero_id'), primary_key=True)
    draft_type = Column(String, primary_key=True, comment='ban vote, system generated ban, ban, pick')
    draft_order = Column(Integer)
    is_random = Column(Boolean)
    by_steam_id = Column(BigInteger, ForeignKey('account.steam_id'), nullable=True)

    def __str__(self):
        type = self.draft_type
        no = f' #{self.draft_order}' if self.draft_order is not None else ''
        return f'<[m] Draft: {type}{no} for hero={self.hero_id}>'


class MatchEvent(Base):
    """

    Types:
    - Ability Learn
    - Ability Use
    - Item Purchase
    - Item Use
    - Kill
    - Death
    - Assist
    - Creep Kill
    - Creep Deny
    - Gold Change
    - Experience Change
    - Buyback
    - Courier Death
    - Ward Placed
    - Ward Destroyed
    - Roshan Death
    - Building Death
    - Rune Spawn
    - Rune Taken
    """
    __tablename__ = 'match_event'

    match_id = Column(BigInteger, ForeignKey('match.match_id'), primary_key=True)
    id = Column(Integer, primary_key=True)
    event_type = Column(String)
    time = Column(Integer)
    x = Column(Integer)
    y = Column(Integer)
    hero_id = Column(SmallInteger, ForeignKey('hero.hero_id'), nullable=True)
    npc_id = Column(Integer, ForeignKey('non_player_character.npc_id'), nullable=True)
    ability_id = Column(Integer, ForeignKey('ability.ability_id'), nullable=True)
    item_id = Column(Integer, ForeignKey('item.item_id'), nullable=True)
    extra_data = Column(JSON)

    def __str__(self):
        name = self.event_type
        time = self.time
        return f'<[m] MatchEvent {name} @ {time} in {self.match_id}>'
