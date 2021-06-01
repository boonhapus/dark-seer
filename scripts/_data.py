import pathlib

from sqlalchemy.ext.asyncio import AsyncSession
from darkseer.informants import Stratz
from darkseer.database import Database
from darkseer.models import (
    GameVersion, Tournament,
    Hero, HeroHistory, Item, ItemHistory, NPC, NPCHistory, Ability, AbilityHistory
)
from darkseer.util import upsert
from typer import Argument as A_, Option as O_
import sqlalchemy as sa
import typer

from .common import to_csv, chunks
from ._async import _coro
from ._db import db_options
from ._ux import console, RichGroup, RichCommand


app = typer.Typer(
    help="""
    Collect data from a number of different informants.
    """,
    cls=RichGroup
)

stratz_app = typer.Typer(help='Collect data from Stratz.', cls=RichGroup)
app.add_typer(stratz_app, name='stratz')


async def get_patches_since(*, sess: AsyncSession, patch: str, since: bool):
    """
    """
    stmt = sa.select(GameVersion.patch_id, GameVersion.patch)

    if patch is None:
        patch = '7.00'
        since = True

    if since:
        stmt = stmt.filter(GameVersion.patch >= patch)
    else:
        stmt = stmt.filter(GameVersion.patch == patch)

    return await sess.execute(stmt)


@stratz_app.command(cls=RichCommand)
@db_options
@_coro
async def patch(
    patch: str=O_(None, help='Specific patch to get data for.'),
    save_path: pathlib.Path=O_(None, help='Directory to save data pull to.'),
    token: str=O_(
        None, help='STRATZ Bearer token for elevated requests permission.',
        envvar='DARKSEER_STRATZ_TOKEN', show_envvar=False
    ),
    **db_options
):
    """
    Collect Game Version data.
    """
    db = Database(**db_options)

    async with Stratz(bearer_token=token) as api:
        with console.status('collecting data on patches..'):
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
    # matches: bool=O_(False, '--matches', help='Whether or not to pull data on matches.'),
    league_id: int=O_(None, help='Specific league to get data for.'),
    save_path: pathlib.Path=O_(None, help='Directory to save data pull to.'),
    token: str=O_(
        None, help='STRATZ Bearer token for elevated requests permission.',
        envvar='DARKSEER_STRATZ_TOKEN', show_envvar=False
    ),
    **db_options
):
    """
    Collect Tournament data.
    """
    db = Database(**db_options)

    async with Stratz(bearer_token=token) as api:
        with console.status('collecting data on tournaments..'):
            leagues = await api.tournaments()

        # if matches:
        #     matches = []

        #     with console.status('collecting match data on ..') as status:
        #         for league in leagues:
        #             status.update(f'collecting match data on {league.league_name}')
        #             r = await api.tournament_matches(league_id=league.league_id)
        #             matches.extend(r)

    if save_path is not None:
        to_csv(save_path / 'tournaments.csv', data=[v.dict() for v in leagues])

        # if matches:
        #     to_csv(save_path / 'matches.csv', data=[v.dict() for v in matches])

    async with db.session() as sess:
        stmt = upsert(Tournament).values([v.dict() for v in leagues])
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
    Collect Hero history data.
    """
    db = Database(**db_options)

    async with db.session() as sess:
        patches = await get_patches_since(sess=sess, patch=patch, since=since)

    heroes = []
    history = []

    async with Stratz(bearer_token=token) as api:
        with console.status('collecting data on patch..') as status:
            for id_, patch in patches:
                status.update(f'collecting data on patch.. {patch}')
                r = await api.heroes(patch_id=id_)
                history.extend(r)
                heroes.extend([
                    schema.to_hero()
                    for schema in r
                    if schema.hero_id not in [h.hero_id for h in heroes]
                ])

    if save_path is not None:
        to_csv(save_path / 'heroes.csv', data=[v.dict() for v in hero])
        to_csv(save_path / 'hero_history.csv', data=[v.dict() for v in history])

    async with db.session() as sess:
        stmt = upsert(Hero).values([v.dict() for v in heroes])
        await sess.execute(stmt)

        for chunk in chunks(history, n=1000):
            stmt = upsert(HeroHistory).values([v.dict() for v in chunk])
            await sess.execute(stmt)


@stratz_app.command(cls=RichCommand)
@db_options
@_coro
async def item(
    patch: str=O_(None, help='Game Version of the Hero to get data for.'),
    since: bool=O_(False, '--since', help='Get data on all patches since.'),
    item_id: str=O_(None, help='Specific Item to get data for.'),
    save_path: pathlib.Path=O_(None, help='Directory to save data pull to.'),
    token: str=O_(
        None, help='STRATZ Bearer token for elevated requests permission.',
        envvar='DARKSEER_STRATZ_TOKEN', show_envvar=False
    ),
    **db_options
):
    """
    Collect Item history data.
    """
    db = Database(**db_options)

    async with db.session() as sess:
        patches = await get_patches_since(sess=sess, patch=patch, since=since)

    items = []
    history = []

    async with Stratz(bearer_token=token) as api:
        with console.status('collecting data on patch..') as status:
            for id_, patch in patches:
                status.update(f'collecting data on patch.. {patch}')
                r = await api.items(patch_id=id_)
                history.extend(r)
                items.extend([
                    schema.to_item()
                    for schema in r
                    if schema.item_id not in [i.item_id for i in items]
                ])

    if save_path is not None:
        to_csv(save_path / 'items.csv', data=[v.dict() for v in items])
        to_csv(save_path / 'item_history.csv', data=[v.dict() for v in history])

    with console.status('writing data to darskeer database..') as status:
        async with db.session() as sess:
            stmt = upsert(Item).values([v.dict() for v in items])
            await sess.execute(stmt)

            for chunk in chunks(history, n=2000):
                stmt = upsert(ItemHistory).values([v.dict() for v in chunk])
                await sess.execute(stmt)


@stratz_app.command(cls=RichCommand)
@db_options
@_coro
async def npc(
    patch: str=O_(None, help='Game Version of the Hero to get data for.'),
    since: bool=O_(False, '--since', help='Get data on all patches since.'),
    npc_id: str=O_(None, help='Specific NPC to get data for.'),
    save_path: pathlib.Path=O_(None, help='Directory to save data pull to.'),
    token: str=O_(
        None, help='STRATZ Bearer token for elevated requests permission.',
        envvar='DARKSEER_STRATZ_TOKEN', show_envvar=False
    ),
    **db_options
):
    """
    Collect NPC history data.
    """
    db = Database(**db_options)

    async with db.session() as sess:
        patches = await get_patches_since(sess=sess, patch=patch, since=since)

    npcs = []
    history = []

    async with Stratz(bearer_token=token) as api:
        with console.status('collecting data on patch..') as status:
            for id_, patch in patches:
                status.update(f'collecting data on patch.. {patch}')
                r = await api.npcs(patch_id=id_)
                history.extend(r)
                npcs.extend([
                    schema.to_npc()
                    for schema in r
                    if schema.npc_id not in [i.npc_id for i in npcs]
                ])

    if save_path is not None:
        to_csv(save_path / 'npcs.csv', data=[v.dict() for v in npc])
        to_csv(save_path / 'npc_history.csv', data=[v.dict() for v in history])

    with console.status('writing data to darskeer database..') as status:
        async with db.session() as sess:
            stmt = upsert(NPC).values([v.dict() for v in npcs])
            await sess.execute(stmt)

            for chunk in chunks(history, n=2000):
                stmt = upsert(NPCHistory).values([v.dict() for v in chunk])
                await sess.execute(stmt)


@stratz_app.command(cls=RichCommand)
@db_options
@_coro
async def ability(
    patch: str=O_(None, help='Game Version of the Hero to get data for.'),
    since: bool=O_(False, '--since', help='Get data on all patches since.'),
    ability_id: str=O_(None, help='Specific Ability to get data for.'),
    save_path: pathlib.Path=O_(None, help='Directory to save data pull to.'),
    token: str=O_(
        None, help='STRATZ Bearer token for elevated requests permission.',
        envvar='DARKSEER_STRATZ_TOKEN', show_envvar=False
    ),
    **db_options
):
    """
    Collect Ability history data.
    """
    db = Database(**db_options)

    async with db.session() as sess:
        patches = await get_patches_since(sess=sess, patch=patch, since=since)

    abilities = []
    history = []

    async with Stratz(bearer_token=token) as api:
        with console.status('collecting data on patch..') as status:
            for id_, patch in patches:
                status.update(f'collecting data on patch.. {patch}')
                r = await api.abilities(patch_id=id_)
                history.extend(r)
                abilities.extend([
                    schema.to_ability()
                    for schema in r
                    if schema.ability_id not in [i.ability_id for i in abilities]
                ])

    if save_path is not None:
        to_csv(save_path / 'abilities.csv', data=[v.dict() for v in ability])
        to_csv(save_path / 'ability_history.csv', data=[v.dict() for v in history])

    with console.status('writing data to darskeer database..') as status:
        async with db.session() as sess:
            stmt = upsert(Ability).values([v.dict() for v in abilities])
            await sess.execute(stmt)

            for chunk in chunks(history, n=2000):
                stmt = upsert(AbilityHistory).values([v.dict() for v in chunk])
                await sess.execute(stmt)
