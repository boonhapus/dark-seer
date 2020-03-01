from sqlalchemy import (
    Column, ForeignKey,
    Date, Integer, String
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


class Match(Base):
    __tablename__ = 'match'


class MatchDraft(Base):
    __tablename__ = 'match_draft'


class MatchPlayer(Base):
    __tablename__ = 'match_player'


class MatchEvent(Base):
    __tablename__ = 'match_event'
