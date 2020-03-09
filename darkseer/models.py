from sqlalchemy import (
    Column, ForeignKey, relationship,
    Date, DateTime, Integer, Float, Boolean, String
)

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


class Hero(Base):
    __tablename__ = 'hero'
    hero_id = Column(Integer, primary_key=True, autoincrement=False)
    patch_id = Column(Integer, ForeignKey('game_version.patch_id'), primary_key=True)
    hero_display_name = Column(String)
    hero_internal_name = Column(String)
    hero_uri = Column(String)
    is_available_captains_mode = Column(Boolean)
    base_agi = Column(Float)
    gain_agi = Column(Float)
    base_str = Column(Float)
    gain_str = Column(Float)
    base_int = Column(Float)
    gain_int = Column(Float)
    ...


class Ability(Base):
    __tablename__ = 'ability'
    ability_id = Column(Integer, primary_key=True, autoincrement=False)
    patch_id = Column(Integer, ForeignKey('game_version.patch_id'), primary_key=True)
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

    matches = relationship('Match', back_populates='tournament')


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

    tournament = relationship('Tournament', back_populates='matches')
    draft = relationship('MatchDraft', back_populates='match')
    # TODO: players = relationship()
    # TODO: events = relationship()


class MatchDraft(Base):
    __tablename__ = 'match_draft'

    match_id = Column(Integer, ForeignKey('match.match_id'), primary_key=True)
    hero_id = Column(Integer, ForeignKey('hero.hero_id'), primary_key=True)
    draft_type = Column(String, primary_key=True, comment='ban_vote, ban, pick')
    order = Column(Integer)
    by_player_id = Column(Integer, ForeignKey('match_player.player_id'))
    by_team = Column(String, comment='radiant, dire')

    match = relationship('Match', back_populates='draft')


class MatchPlayer(Base):
    __tablename__ = 'match_player'

    # game_movement = relationship('PlayerMovement', back_populates='player')


class PlayerMovement(Base):
    __tablename__ = 'player_movement'

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey('match.match_id'))
    hero_id = Column(Integer, ForeignKey('match_player.hero_id'))
    time = Column(Integer)
    x = Column(Integer)
    y = Column(Integer)

    match = relationship('Match')
    player = relationship('MatchPlayer', back_populates='game_movement')


class MatchEvent(Base):
    __tablename__ = 'match_event'
