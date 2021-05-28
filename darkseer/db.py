from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


class Database:

    def __init__(
        self,
        host: str,
        *,
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

    @property
    def session(self):
        return self._Session
