import sqlalchemy as sa

from darkseer.database import Base


# elements which exist w.r.t the game of dota

class Hero(Base):
    __tablename__ = 'hero'

class Ability(Base):
    __tablename__ = 'ability'

class Item(Base):
    __tablename__ = 'item'


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
