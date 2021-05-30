from sqlalchemy import (
    Column, ForeignKey, ForeignKeyConstraint,
    Date, DateTime, Integer, BigInteger, Float, Boolean, String
)
from sqlalchemy.dialects.postgresql import JSON
# from sqlalchemy.orm import relationship

from darkseer.database import Base


class Account(Base):
    __tablename__ = 'account'

    steam_id = Column(BigInteger, primary_key=True, autoincrement=False)
    steam_name = Column(String)

    def __str__(self):
        name = self.steam_name
        return f'<[m] Account name={name}>'


class CompetitiveTeam(Base):
    __tablename__ = 'competitive_team'

    team_id = Column(BigInteger, primary_key=True)
    team_name = Column(String)
    team_tag = Column(String)
    country_code = Column(String)
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
    prize_pool = Column(BigInteger)

    def __str__(self):
        name = self.league_name
        date = self.league_start_date.strftime('%Y-%m-%d')
        prize = self.prize_pool
        n_matches = len(self.matches)
        return f'<[m] Tournament: [{date}] {name} ({n_matches} matches) ${prize:,}>'


class GameVersion(Base):
    __tablename__ = 'game_version'

    patch_id = Column(Integer, primary_key=True, autoincrement=False)
    patch = Column(String)
    release_dt = Column(DateTime)

    def __str__(self):
        patch = self.patch
        return f'<[m] GameVersion patch={patch}>'


class Hero(Base):
    __tablename__ = 'hero'

    hero_id = Column(Integer, primary_key=True, autoincrement=False)
    # patch_id = Column(Integer, ForeignKey('game_version.patch_id'), primary_key=True)
    hero_display_name = Column(String)
    hero_internal_name = Column(String)

    def __str__(self):
        name = self.display_name
        return f'<[m] Hero {name}>'


class Match(Base):
    __tablename__ = 'match'

    match_id = Column(BigInteger, primary_key=True, autoincrement=False)
    patch_id = Column(Integer, ForeignKey('game_version.patch_id'))
    league_id = Column(BigInteger, ForeignKey('tournament.league_id'))
    radiant_team_id = Column(BigInteger, ForeignKey('competitive_team.team_id'))
    dire_team_id = Column(BigInteger, ForeignKey('competitive_team.team_id'))
    start_datetime = Column(DateTime, comment='held as naive, but UTC')
    is_stats = Column(Boolean)
    is_radiant_win = Column(Boolean)
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
    hero_id = Column(Integer, ForeignKey('hero.hero_id'), primary_key=True)
    steam_id = Column(BigInteger, ForeignKey('account.steam_id'))
    slot = Column(Integer)
    party_id = Column(Integer)
    is_leaver = Column(Integer)

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

    __table_args__ = (
        ForeignKeyConstraint([match_id, hero_id], [MatchPlayer.match_id, MatchPlayer.hero_id]),
        {}
    )

    def __str__(self):
        hero = self.hero.display_name
        time = self.time
        x = self.x
        y = self.y
        return f'<[m] Movement of {hero} @ {time} loc: ({x}, {y})>'


class MatchDraft(Base):
    __tablename__ = 'match_draft'

    match_id = Column(BigInteger, ForeignKey('match.match_id'), primary_key=True)
    hero_id = Column(Integer, ForeignKey('hero.hero_id'), primary_key=True)
    draft_type = Column(String, primary_key=True, comment='ban vote, ban, pick')
    draft_order = Column(Integer)
    is_random = Column(Integer)
    by_steam_id = Column(Integer, ForeignKey('account.steam_id'), nullable=True)

    def __str__(self):
        type = self.draft_type
        no = f' #{self.draft_order}' if self.draft_order is not None else ''
        return f'<[m] Draft: {type}{no} for hero={self.hero_id}>'


# class MatchEvent(Base):
#     """

#     Types:
#     - Ability Learn
#     - Ability Use
#     - Item Purchase
#     - Item Use
#     - Kill
#     - Death
#     - Assist
#     - Creep Kill
#     - Creep Deny
#     - Gold Change
#     - Experience Change
#     - Buyback
#     - Courier Death
#     - Ward Placed
#     - Ward Destroyed
#     - Roshan Death
#     - Building Death
#     - Rune Spawn
#     - Rune Taken
#     """
#     __tablename__ = 'match_event'

#     id = Column(Integer, primary_key=True)
#     match_id = Column(Integer, ForeignKey('match.match_id'))
#     event_type = Column(String)
#     hero_id = Column(Integer, ForeignKey('hero.hero_id'), nullable=True)
#     npc_id = Column(Integer, ForeignKey('non_player_character.npc_id'), nullable=True)
#     ability_id = Column(Integer, ForeignKey('ability.ability_id'), nullable=True)
#     item_id = Column(Integer, ForeignKey('item.item_id'), nullable=True)
#     time = Column(Integer)
#     x = Column(Integer)
#     y = Column(Integer)
#     extra_data = Column(JSON)

#     def __str__(self):
#         name = self.event_type
#         time = self.time
#         return f'<[m] MatchEvent {name} @ {time} in {self.match_id}>'
