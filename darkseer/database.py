from contextlib import contextmanager
import logging

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session, Session
import sqlalchemy as sa


Base = declarative_base()
log = logging.getLogger(__name__)


class Database:
    def __init__(self, conn_string: str):
        self._engine = sa.create_engine(conn_string)
        self._session_factory = sessionmaker(bind=self._engine)
        self._Session = scoped_session(self._session_factory)

    @property
    def engine(self):
        return self._engine

    @contextmanager
    def session(self, **kwargs) -> Session:
        """
        Handles all the messy details of session work.
        """
        self._session = sess = self._Session(**kwargs)

        try:
            yield sess
            sess.commit()
        except Exception as e:
            sess.rollback()
            log.exception(f'{type(e).__name__}: {e}')
            # raise e
        finally:
            sess.close()
            self._session = None

    def __repr__(self):
        return f'<Database {self._engine.url}>'
