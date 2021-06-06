import pathlib

from sqlalchemy.ext.asyncio import AsyncSession
from darkseer.informants import Stratz
from darkseer.database import Database
from darkseer.models import (
    GameVersion, Tournament, Account,
    Hero, HeroHistory, Item, ItemHistory, NPC, NPCHistory, Ability, AbilityHistory,
    Match, CompetitiveTeam, MatchDraft, MatchPlayer, HeroMovement  # , MatchEvent
)
from darkseer.util import upsert, chunks
from typer import Argument as A_, Option as O_
import sqlalchemy as sa
import typer

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


async def write_matches(sess, r):
    """
    """
    r = [m.dict() for m in r]
    deps = ('tournament', 'teams', 'accounts', 'draft', 'players', 'hero_movements', 'events')

    t = [m['tournament'] for m in r]
    for chunk in chunks(t, n=5000):
        stmt = upsert(Tournament).values(chunk)
        await sess.execute(stmt)

    c = [c for m in r for c in m['teams']]
    for chunk in chunks(c, n=6000):
        stmt = upsert(CompetitiveTeam).values(chunk)
        await sess.execute(stmt)

    m = [{k: v for k, v in m.items() if k not in deps} for m in r]
    for chunk in chunks(m, n=2500):
        stmt = upsert(Match).values(chunk)
        await sess.execute(stmt)

    a = [a for m in r for a in m['accounts']]
    for chunk in chunks(a, n=10000):
        stmt = upsert(Account).values(chunk)
        await sess.execute(stmt)

    d = [d for m in r for d in m['draft']]
    for chunk in chunks(d, n=5000):
        stmt = upsert(MatchDraft).values(chunk)
        await sess.execute(stmt)

    p = [p for m in r for p in m['players']]
    for chunk in chunks(p, n=3000):
        stmt = upsert(MatchPlayer).values(chunk)
        await sess.execute(stmt)

    x = [x for m in r for x in m['hero_movements']]
    for chunk in chunks(x, n=5000):
        stmt = upsert(HeroMovement).values(chunk)
        await sess.execute(stmt)

    # stmt = upsert(MatchEvent).values([e for m in r for e in m['events']])
    # await sess.execute(stmt)


@stratz_app.command(cls=RichCommand)
@db_options
@_coro
async def patch(
    patch: str=O_(None, help='Specific patch to get data for.'),
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

    with console.status('writing data to darskeer database..') as status:
        async with db.session() as sess:
            stmt = upsert(GameVersion).values([v.dict() for v in r])
            await sess.execute(stmt)


@stratz_app.command(cls=RichCommand)
@db_options
@_coro
async def tournament(
    matches: bool=O_(False, '--matches', help='Whether or not to pull data on matches.'),
    league_id: int=O_(None, help='Specific league to get data for.'),
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

        if matches:
            matches = []

            with console.status('collecting match data on ..') as status:
                for league in leagues:
                    status.update(f'collecting match data on {league.league_name}')
                    r = await api.tournament_matches(league_id=league.league_id)
                    matches.extend(r)

    with console.status('writing data to darskeer database..') as status:
        async with db.session() as sess:
            await write_matches(sess, matches)


@stratz_app.command(cls=RichCommand)
@db_options
@_coro
async def match(
    match_id: int=O_(None, help='Match ID to get data for.'),
    token: str=O_(
        None, help='STRATZ Bearer token for elevated requests permission.',
        envvar='DARKSEER_STRATZ_TOKEN', show_envvar=False
    ),
    **db_options
):
    """
    Collect Match data.
    """
    db = Database(**db_options)

    async with Stratz(bearer_token=token) as api:
        with console.status(f'collecting data on match {match_id}..'):
            r = await api.matches(match_ids=[match_id])

    with console.status('writing data to darskeer database..') as status:
        async with db.session() as sess:
            await write_matches(sess, r)


@stratz_app.command(cls=RichCommand)
@db_options
@_coro
async def hero(
    patch: str=O_(None, help='Game Version of the Hero to get data for.'),
    since: bool=O_(False, '--since', help='Get data on all patches since.'),
    hero_id: str=O_(None, help='Specific Hero to get data for.'),
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

    with console.status('writing data to darskeer database..') as status:
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

    with console.status('writing data to darskeer database..') as status:
        async with db.session() as sess:
            stmt = upsert(Ability).values([v.dict() for v in abilities])
            await sess.execute(stmt)

            for chunk in chunks(history, n=2000):
                stmt = upsert(AbilityHistory).values([v.dict() for v in chunk])
                await sess.execute(stmt)
