import sqlalchemy as sa

from darkseer.database import Base


# elements which exist w.r.t the game of dota

class GameVersion(Base):
    __tablename__ = 'game_version'
    patch_id = Column(Integer, primary_key=True)
    patch = Column(String)
    release_datetime = Column(DateTime, comment='held as naive, but UTC')

class Hero(Base):
    __tablename__ = 'hero'
    hero_id = Column(Integer, primary_key=True, autoincrement=False)
    ...

class Ability(Base):
    __tablename__ = 'ability'
    ability_id = Column(Integer, primary_key=True, autoincrement=False)
    ...

class Item(Base):
    __tablename__ = 'item'
    item_id = Column(Integer, primary_key=True, autoincrement=False)
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
