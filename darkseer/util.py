from typing import List
import asyncio
import time

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.inspection import inspect
import sqlalchemy as sa
import httpx

from ._version import __version__


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
        return self.tokens / self.seconds

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

    async def get(self, *a, **kw):
        """
        HTTP GET.
        """
        await self.wait_for_token()
        return await super().get(*a, **kw)

    async def post(self, *a, **kw):
        """
        HTTP POST.
        """
        await self.wait_for_token()
        return await super().post(*a, **kw)


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
