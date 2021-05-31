import pathlib

from darkseer.informants import Stratz
from darkseer.database import Database
from darkseer.models import (
    GameVersion, Tournament, Hero, HeroHistory
)
from darkseer.util import upsert
from typer import Argument as A_, Option as O_
import sqlalchemy as sa
import typer

from .common import to_csv, chunks
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


@stratz_app.command(cls=RichCommand)
@db_options
@_coro
async def hero(
    patch: str=O_(None, help='Game Version of the Hero to get data for.'),
    since: bool=O_(False, '--since', help='Get data on all patches since.'),
    hero_id: str=O_(None, help='Specific Hero to get data for.'),
    save_path: pathlib.Path=O_(None, help='Directory to save data pull to.'),
    token: str=O_(
        None, help='STRATZ Bearer token for elevated requests permission.',
        envvar='DARKSEER_STRATZ_TOKEN', show_envvar=False
    ),
    **db_options
):
    """

    """
    db = Database(**db_options)

    async with db.session() as sess:
        maxp = sa.select(sa.func.max(GameVersion.patch_id)).as_scalar()
        stmt = sa.select(GameVersion.patch_id, maxp == GameVersion.patch_id)

        if patch is None:
            patch = '7.00'
            since = True

        if since:
            stmt = stmt.filter(GameVersion.patch >= patch)
        else:
            stmt = stmt.filter(GameVersion.patch == patch)

        rows = await sess.execute(stmt)
        patch_ids = [r for r in rows]

    heroes = []
    history = []

    async with Stratz(bearer_token=token) as api:
        for patch, is_latest in patch_ids:
            r = await api.heroes(patch_id=patch)
            history.extend(r)

            if is_latest:
                heroes.extend([schema.to_hero() for schema in r])

    if save_path is not None:
        to_csv(save_path / 'heroes.csv', data=[v.dict() for v in r])

    async with db.session() as sess:
        stmt = upsert(Hero).values([v.dict() for v in heroes])
        await sess.execute(stmt)

        for chunk in chunks(history, n=1000):
            stmt = upsert(HeroHistory).values([v.dict() for v in chunk])
            await sess.execute(stmt)

