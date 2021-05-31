import pathlib

from darkseer.informants import Stratz
from darkseer.database import Database
from darkseer.models import GameVersion, Tournament
from darkseer.util import upsert
from typer import Argument as A_, Option as O_
import typer

from .common import to_csv
from ._async import _coro
from ._db import db_options
from ._ux import console, RichGroup, RichCommand


app = typer.Typer(help='Perform data functions.', cls=RichGroup)

stratz_app = typer.Typer(help='Collect data from Stratz.', cls=RichGroup)
app.add_typer(stratz_app, name='stratz')


@stratz_app.command(cls=RichCommand)
@db_options
@_coro
async def patch(
    patch: str=O_(None, help='Specific patch to get data for.'),
    save_path: pathlib.Path=O_(None, help='Directory to save data pull to.'),
    token: str=O_(None, help='STRATZ Bearer token for elevated requests permission'),
    **db_options
):
    """

    """
    db = Database(**db_options)

    async with Stratz(bearer_token=token) as api:
        r = await api.patches()

    if save_path is not None:
        to_csv(save_path / 'patches.csv', data=[v.dict() for v in r])

    async with db.session() as sess:
        stmt = upsert(GameVersion).values([v.dict() for v in r])
        await sess.execute(stmt)


@stratz_app.command(cls=RichCommand)
@db_options
@_coro
async def tournament(
    league_id: str=O_(None, help='Specific league to get data for.'),
    save_path: pathlib.Path=O_(None, help='Directory to save data pull to.'),
    token: str=O_(None, help='STRATZ Bearer token for elevated requests permission'),
    **db_options
):
    """

    """
    db = Database(**db_options)

    async with Stratz(bearer_token=token) as api:
        r = await api.tournaments()

    if save_path is not None:
        to_csv(save_path / 'tournaments.csv', data=[v.dict() for v in r])

    async with db.session() as sess:
        stmt = upsert(Tournament).values([v.dict() for v in r])
        await sess.execute(stmt)
