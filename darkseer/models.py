from sqlalchemy import (
    Column, ForeignKey, relationship,
    Date, DateTime, Integer, Float, Boolean, String
)
from sqlalchemy.postgresql import JSON

from darkseer.database import Base


# elements which exist w.r.t the game of dota

class GameVersion(Base):
    __tablename__ = 'game_version'

    patch_id = Column(Integer, primary_key=True)
    patch = Column(String)
    release_date = Column(Date, comment='held as naive, but UTC')


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
    __tablename__ = 'non_player_character'

    npc_id = Column(Integer, primary_key=True)
    patch_id = Column(Integer, primary_key=True)
    npc_name = Column(String)


class Hero(Base):
    __tablename__ = 'hero'

    hero_id = Column(Integer, primary_key=True)
    patch_id = Column(Integer, ForeignKey('game_version.patch_id'), primary_key=True)
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


class Ability(Base):
    __tablename__ = 'ability'

    ability_id = Column(Integer, primary_key=True, autoincrement=False)
    patch_id = Column(Integer, ForeignKey('game_version.patch_id'), primary_key=True)
    ...


class HeroTalent(Base):
    __tablename__ = 'hero_talent'

    hero_id = Column(Integer, ForeignKey('hero.hero_id'), primary_key=True)
    ability_id = Column(Integer, ForeignKey('ability.ability_id'), primary_key=True)
    patch_id = Column(Integer, ForeignKey('game_version.patch_id'), primary_key=True)
    is_left_side = Column(Boolean)
    ...


class HeroSkill(Base):
    __tablename__ = 'hero_skill'

    hero_id = Column(Integer, ForeignKey('hero.hero_id'), primary_key=True)
    ability_id = Column(Integer, ForeignKey('ability.ability_id'), primary_key=True)
    patch_id = Column(Integer, ForeignKey('game_version.patch_id'), primary_key=True)
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
    patch_id = Column(Integer, ForeignKey('game_version.patch_id'), primary_key=True)
    ...


# elements which exist w.r.t. a Match of dota

class Tournament(Base):
    __tablename__ = 'tournament'

    league_id = Column(Integer, primary_key=True)
    league_name = Column(String)
    league_start_date = Column(Date, comment='held as naive, but UTC')
    league_end_date = Column(Date, comment='held as naive, but UTC')
    prize_pool = Column(Integer)

    # matches = relationship('Match', back_populates='tournament')


class Match(Base):
    __tablename__ = 'match'

    match_id = Column(Integer, primary_key=True)
    patch_id = Column(Integer, ForeignKey('game_version.patch_id'))
    league_id = Column(Integer, ForeignKey('tournament.league_id'))
    series_id = Column(Integer)  # we can make a VIEW for Tournament games
    region = Column(String)
    lobby_type = Column(String)
    game_mode = Column(String)
    start_datetime = Column(DateTime, comment='held as naive, but UTC')
    duration = Column(Integer, comment='held as seconds')
    average_rank = Column(Integer)
    is_radiant_win = Column(Boolean)

    # tournament = relationship('Tournament', back_populates='matches')
    # draft = relationship('MatchDraft', back_populates='match')
    # players = relationship('MatchPlayer', back_populates='match')
    # TODO: events = relationship()


class MatchDraft(Base):
    __tablename__ = 'match_draft'

    match_id = Column(Integer, ForeignKey('match.match_id'), primary_key=True)
    hero_id = Column(Integer, ForeignKey('hero.hero_id'), primary_key=True)
    draft_type = Column(String, primary_key=True, comment='ban_vote, ban, pick')
    order = Column(Integer)
    by_player_id = Column(Integer, ForeignKey('match_player.player_id'))
    by_team = Column(String, comment='radiant, dire')

    # match = relationship('Match', back_populates='draft')


class MatchPlayer(Base):
    __tablename__ = 'match_player'

    match_id = Column(Integer, ForeignKey('match.match_id'), primary_key=True)
    slot = Column(Integer, primary_key=True)
    hero_id = Column(Integer, ForeignKey('hero.hero_id'))
    steam_id = Column(Integer)
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

    # match = relationship('Match', back_populates='players')
    # game_movement = relationship('PlayerMovement', back_populates='player')


class PlayerMovement(Base):
    __tablename__ = 'player_movement'

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey('match.match_id'))
    hero_id = Column(Integer, ForeignKey('match_player.hero_id'))
    time = Column(Integer)
    x = Column(Integer)
    y = Column(Integer)

    # match = relationship('Match')
    # player = relationship('MatchPlayer', back_populates='game_movement')


class MatchEvent(Base):
    __tablename__ = 'match_event'

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey('match.match_id'))
    event_type_id = Column(Integer, ForeignKey('match_event_type.event_type_id'))
    hero_id = Column(Integer, ForeignKey('hero.hero_id'))
    npc_id = Column(Integer, ForeignKey('non_player_character.npc_id'))
    ability_id = Column(Integer, ForeignKey('ability.ability_id'))
    item_id = Column(Integer, ForeignKey('item.item_id'))
    time = Column(Integer)
    x = Column(Integer)
    y = Column(Integer)
    extra_data = Column(JSON)


class MatchEventType(Base):
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
    __tablename__ = 'match_event_type'

    event_type_id = Column(Integer, primary_key=True)
    event_type = Column(String)
