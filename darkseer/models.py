from sqlalchemy import (
    Column, ForeignKey, ForeignKeyConstraint,
    Date, DateTime, Integer, Float, Boolean, String
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship

from darkseer.database import Base


class Account(Base):
    __tablename__ = 'account'

    steam_id = Column(Integer, primary_key=True, autoincrement=False)
    discord_id = Column(Integer)
    account_name = Column(String)

    def __str__(self):
        return f'<[m] Account for {self.account_name}>'


# elements which exist w.r.t the game of dota

class GameVersion(Base):
    __tablename__ = 'game_version'

    patch_id = Column(Integer, primary_key=True, autoincrement=False)
    patch = Column(String)
    release_date = Column(Date, comment='held as naive, but UTC')

    # TODO: modelHistory variants
    #
    # .. where the PK is combined on ID + patch_id
    #
    # heroes = relationship('Hero', back_populates='patch')
    # npcs = relationship('NonPlayerCharacter', back_populates='patch')
    # items = relationship('Item', back_populates='patch')
    matches = relationship('Match', back_populates='patch')

    def __str__(self):
        patch = self.patch
        id = self.patch_id
        return f'<[m] GameVersion patch={patch} (id {id})>'


# TODO: ... do we care? These changes are tracked via database entries anyway.
#
# class PatchNotes(Base):
#     __tablename__ = 'patch_notes'
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     patch_id = Column(Integer, ForeignKey('game_version.patch_id'), primary_key=True)
#     hero_id = Column(Integer, ForeignKey('hero.hero_id'), nullable=True)
#     ability_id = Column(Integer, ForeignKey('ability.ability_id'), nullable=True)
#     item_id = Column(Integer, ForeignKey('item.item_id'), nullable=True)
#     description = Column(String)


class NonPlayerCharacter(Base):
    """
    Data on NPCs in their latest patch/iteration.
    """
    __tablename__ = 'non_player_character'

    npc_id = Column(Integer, primary_key=True, autoincrement=False)
    npc_name = Column(String)

    def __str__(self):
        name = self.npc_name
        id = self.npc_id
        return f'<[m] NPC {name} (id {id})>'


class Hero(Base):
    """
    Data on Heroes in their latest patch/iteration.
    """
    __tablename__ = 'hero'

    hero_id = Column(Integer, primary_key=True, autoincrement=False)
    hero_display_name = Column(String)
    hero_internal_name = Column(String)
    hero_uri = Column(String)
    faction = Column(String, comment='radiant, dire')
    is_available_captains_mode = Column(Boolean)
    vision_day = Column(Integer)
    vision_night = Column(Integer)
    is_melee = Column(Boolean)
    turn_rate = Column(Boolean)
    base_movespeed = Column(Integer)
    attack_point = Column(Float)      # STRATZ: attackAnimationPoint
    base_attack_time = Column(Float)  # STRATZ: attackRate
    attack_range = Column(Float)
    primary_attr = Column(String)
    base_agi = Column(Float)
    gain_agi = Column(Float)
    base_str = Column(Float)
    gain_str = Column(Float)
    base_int = Column(Float)
    gain_int = Column(Float)
    base_armor = Column(Float)
    base_magic_armor = Column(Float)

    def __str__(self):
        name = self.display_name
        id = self.hero_id
        return f'<[m] Hero {name} (id {id})>'


class Ability(Base):
    __tablename__ = 'ability'

    ability_id = Column(Integer, primary_key=True, autoincrement=False)
    ...


class HeroTalent(Base):
    __tablename__ = 'hero_talent'

    hero_id = Column(Integer, ForeignKey('hero.hero_id'), primary_key=True)
    ability_id = Column(Integer, ForeignKey('ability.ability_id'), primary_key=True)
    is_left_side = Column(Boolean)
    ...


class HeroSkill(Base):
    __tablename__ = 'hero_skill'

    hero_id = Column(Integer, ForeignKey('hero.hero_id'), primary_key=True)
    ability_id = Column(Integer, ForeignKey('ability.ability_id'), primary_key=True)
    # NOTE:
    #
    # Array vs REL_HeroSkillLevel?
    #
    # - skills increase in potency with levels
    #
    # skill_level = Column(Integer)
    ...


class Item(Base):
    __tablename__ = 'item'

    item_id = Column(Integer, primary_key=True, autoincrement=False)
    ...

    def __str__(self):
        name = self.display_name
        id = self.item_id
        return f'<[m] Item {name} (id {id})>'


class CompetitiveTeam(Base):
    __tablename__ = 'competitive_team'

    team_id = Column(Integer, primary_key=True)
    team_name = Column(String)
    ...

    def __str__(self):
        name = self.team_name
        id = self.team_id
        return f'<[m] Team {name} (id {id})>'


# elements which exist w.r.t. a Match of dota

class Tournament(Base):
    __tablename__ = 'tournament'

    league_id = Column(Integer, primary_key=True)
    league_name = Column(String)
    league_start_date = Column(Date, comment='held as naive, but UTC')
    league_end_date = Column(Date, comment='held as naive, but UTC')
    prize_pool = Column(Integer)

    matches = relationship('Match', back_populates='tournament')

    def __str__(self):
        name = self.league_name
        date = self.league_start_date.strftime('%Y-%m-%d')
        prize = self.prize_pool
        n_matches = len(self.matches)
        return f'<[m] Tournament: [{date}] {name} ({n_matches} matches) ${prize:,}>'


class Match(Base):
    __tablename__ = 'match'

    match_id = Column(Integer, primary_key=True)
    region = Column(String)
    lobby_type = Column(String)
    game_mode = Column(String)
    patch_id = Column(Integer, ForeignKey('game_version.patch_id'))
    start_datetime = Column(DateTime, comment='held as naive, but UTC')
    duration = Column(Integer, comment='held as seconds')
    is_radiant_win = Column(Boolean)
    is_stats = Column(Boolean)
    league_id = Column(Integer, ForeignKey('tournament.league_id'))
    series_id = Column(Integer)  # we can make a VIEW for Tournament games
    radiant_team_id = Column(Integer, ForeignKey('competitive_team.team_id'))
    dire_team_id = Column(Integer, ForeignKey('competitive_team.team_id'))
    rank = Column(Integer)

    tournament = relationship('Tournament', back_populates='matches')
    draft = relationship('MatchDraft', back_populates='match')
    players = relationship('MatchPlayer', back_populates='match')
    # TODO: events = relationship()

    def __str__(self):
        ranked = 'Ranked' if self.is_stats else 'Unranked'
        dt = self.start_datetime.strftime('%Y-%m-%d %H:%M:%S %Z')
        id = self.match_id
        winner = 'Radiant' if self.is_radiant_win else 'Dire'
        return f'<[m] {ranked}Match: [{dt}] {id} - Winner: {winner}>'


class MatchPlayer(Base):
    __tablename__ = 'match_player'

    match_id = Column(Integer, ForeignKey('match.match_id'), primary_key=True)
    hero_id = Column(Integer, ForeignKey('hero.hero_id'), primary_key=True)
    slot = Column(Integer)
    steam_id = Column(Integer, ForeignKey('account.steam_id'))
    player_name = Column(String)
    party_id = Column(Integer)
    behavior_score = Column(Integer)
    streak_prediction = Column(Integer)
    role = Column(String)
    kills = Column(Integer)
    deaths = Column(Integer)
    assists = Column(Integer)
    last_hits = Column(Integer)
    denies = Column(Integer)
    gpm = Column(Integer)
    xpm = Column(Integer)
    final_level = Column(Integer)
    player_abandoned = Column(Boolean)

    match = relationship('Match', back_populates='players')
    hero = relationship('Hero')
    game_movement = relationship('PlayerMovement', back_populates='player')

    def __str__(self):
        hero_name = self.hero.display_name
        return f'<[m] Player: slot {self.slot} on {hero_name}>'


class HeroMovement(Base):
    __tablename__ = 'hero_movement'

    match_id = Column(Integer, ForeignKey('match.match_id'), primary_key=True)
    hero_id = Column(Integer, ForeignKey('hero.hero_id'), primary_key=True)
    id = Column(Integer, primary_key=True)
    time = Column(Integer)
    x = Column(Integer)
    y = Column(Integer)

    match = relationship('Match')
    hero = relationship('Hero')

    def __str__(self):
        hero = self.hero.display_name
        time = self.time
        x = self.x
        y = self.y
        return f'<[m] Movement of {hero} @ {time} loc: ({x}, {y})>'


class MatchDraft(Base):
    __tablename__ = 'match_draft'

    match_id = Column(Integer, ForeignKey('match.match_id'), primary_key=True)
    hero_id = Column(Integer, ForeignKey('hero.hero_id'), primary_key=True)
    draft_type = Column(String, primary_key=True, comment='ban vote, ban, pick')
    draft_order = Column(Integer)
    by_steam_id = Column(Integer, ForeignKey('account.steam_id'), nullable=True)

    match = relationship('Match', back_populates='draft')
    hero = relationship('Hero')

    def __str__(self):
        type_ = self.draft_type
        no = f' #{self.draft_order}' if self.draft_order is not None else ''
        return f'<[m] Draft: {type_}{no} for hero={self.hero_id}>'


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

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey('match.match_id'))
    event_type = Column(String)
    hero_id = Column(Integer, ForeignKey('hero.hero_id'), nullable=True)
    npc_id = Column(Integer, ForeignKey('non_player_character.npc_id'), nullable=True)
    ability_id = Column(Integer, ForeignKey('ability.ability_id'), nullable=True)
    item_id = Column(Integer, ForeignKey('item.item_id'), nullable=True)
    time = Column(Integer)
    x = Column(Integer)
    y = Column(Integer)
    extra_data = Column(JSON)

    def __str__(self):
        name = self.event_type
        time = self.time
        return f'<[m] MatchEvent {name} @ {time} in {self.match_id}>'
