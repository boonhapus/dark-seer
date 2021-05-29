from contextlib import asynccontextmanager
import logging

from sqlalchemy.schema import MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import asyncpg


Base = declarative_base()
log = logging.getLogger(__name__)


class Database:
    """
    """
    def __init__(
        self,
        host: str,
        *,
        port: int=None,
        username: str=None,
        password: str=None,
        echo: bool=False
    ):
        auth = (
            ''
            + ('' if username is None else f'{username}')
            + ('' if password is None else f':{password}')
        )

        self._conn_string = f'postgresql+asyncpg://{auth}@{host}/darkseer'
        self._engine = create_async_engine(self._conn_string, echo=echo)
        self._Session = sessionmaker(self._engine, expire_on_commit=False, class_=AsyncSession)
        self._metadata = Base.metadata

    @property
    def engine(self) -> AsyncEngine:
        """
        Public access to the async engine.
        """
        return self._engine

    @property
    def metadata(self) -> MetaData:
        """
        Public access to the Metadata object.
        """
        return self._metadata

    @asynccontextmanager
    async def session(self, **kwargs) -> AsyncSession:
        """
        Handles all the messy details of session work.
        """
        self._session = sess = self._Session(**kwargs)

        try:
            yield sess
            await sess.commit()
        except asyncpg.exceptions.InvalidPasswordError as e:
            log.error(f'{type(e).__name__}: {e}')
        except Exception as e:
            # log.exception(f'{type(e).__name__}: {e}')
            await sess.rollback()
            raise e
        finally:
            await sess.close()
            self._session = None

    def __repr__(self):
        return f'<Database {self._engine.url}>'
