from typing import Any, List, Dict, Callable
import asyncio
import pathlib
import json
import time

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.inspection import inspect
import sqlalchemy as sa
import httpx

from ._version import __version__


class _Response:
    """
    Dummy response object.
    """
    def __init__(self, r):
        self.r = r

    def json(self):
        return self.r

    def raise_for_status(self):
        pass


class FileCache:

    def __init__(self, dir_: pathlib.Path):
        self.dir_ = pathlib.Path(dir_)
        self._cache = {}
        self._latest_n = 0
        self._load_cache()

    @property
    def cache_map(self) -> pathlib.Path:
        return self.dir_ / 'cache_map.json'

    def _load_cache(self):
        if not self.cache_map.exists():
            return

        with self.cache_map.open('r') as j:
            self._cache = json.load(j)

        self._latest_n = max([
            int(fp.split('.json')[0][-1])
            for fp in self._cache.values()
        ])

    def memoize(self, f: Callable) -> List[Dict[str, Any]]:
        """
        Cache the caller's result based on input arguments.
        """
        async def wrapper(*a, **kw):
            unique = map(str, (*a, *kw.keys(), *kw.values()))
            key = '_'.join(unique)

            try:
                fp = self._cache[key]
            except KeyError:
                r = await f(*a, **kw)
                self._latest_n += 1
                fp = self.dir_ / f'{self._latest_n}.json'
                self._cache[key] = str(fp)

                with fp.open('w') as j:
                    json.dump(r.json(), j, indent=4)

                with self.cache_map.open('w') as j:
                    json.dump(self._cache, j, indent=4)

            else:
                with pathlib.Path(fp).open('r') as j:
                    r = _Response(json.load(j))

            return r
        return wrapper


class RateLimitedHTTPClient(httpx.AsyncClient):
    """
    HTTPX client with token rate limiting.
    """
    def __init__(
        self,
        tokens: float,
        seconds: float,
        *,
        max_tokens: float=None,
        **opts
    ):
        super().__init__(**opts)
        self.headers.update({
            'User-agent': f'DarkSeer/{__version__} (+github: dark-seer)'
        })
        self.tokens = tokens
        self.seconds = seconds
        self.max_tokens = max_tokens or tokens
        self.updated_at = time.monotonic()

    @property
    def rate(self) -> float:
        """
        Rate limit expressed as "tokens per second".
        """
        return self.max_tokens / self.seconds

    async def wait_for_token(self):
        """
        Block the context until a token is available.
        """
        while self.tokens < 1:
            self.add_new_tokens()
            await asyncio.sleep(0.1)

        self.tokens -= 1

    def add_new_tokens(self):
        """
        Determine if tokens should be added.
        """
        now = time.monotonic()
        new_tokens = (now - self.updated_at) * self.rate

        if self.tokens + new_tokens >= 1:
            self.tokens = min(self.tokens + new_tokens, self.max_tokens)
            self.updated_at = now

    async def request(self, *a, **kw):
        """
        Make a request, adjusting tokens if necessary.
        """
        r = await super().request(*a, **kw)
        remaining_tokens = int(r.headers['x-ratelimit-remaining-hour']) - 10

        if remaining_tokens < self.tokens:
            self.tokens = max(0, remaining_tokens)

        return r

    async def get(self, *a, **kw):
        """
        HTTP GET.
        """
        await self.wait_for_token()
        return await self.request('GET', *a, **kw)

    async def post(self, *a, **kw):
        """
        HTTP POST.
        """
        await self.wait_for_token()
        return await self.request('POST', *a, **kw)


def upsert(model: sa.Table, *, constraint: List[str]=None) -> sa.sql.Insert:
    """
    Implementation of postgres ON CONFLICT DO UPDATE.

    Parameters
    ----------
    model : sqlalchemy.Table
      table model to upsert into

    constraint : List[str], default: model.primary_key
      unique constraint to hand to ON CONFLICT DO UPDATE, if not
      supplied then we use the model's primary key

    Returns
    -------
    stmt : sqlalchemy.dialects.postgresql.dml.Insert
    """
    if constraint is None:
        constraint = [c.name for c in inspect(model).primary_key]
    if isinstance(constraint, str):
        constraint = [constraint]

    stmt = insert(model)
    stmt = stmt.on_conflict_do_update(
        index_elements=constraint,
        set_={
            excluded.name: excluded
            for excluded in stmt.excluded
            if excluded.name not in constraint
        }
    )
    return stmt
