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


# class Hero(BaseModel):
#     patch_id: int
#     patch: str
#     release_dt: dt.datetime

#     @validator('release_dt', pre=True)
#     def ensure_utc(cls, ts: int) -> dt.datetime:
#         return dt.datetime.utcfromtimestamp(ts)
