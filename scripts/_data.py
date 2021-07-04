from typing import List
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from darkseer.informants.stratz import schema
from darkseer.informants import Stratz, OpenDota
from darkseer.database import Database
from darkseer.models import (
    GameVersion, Tournament, Account,
    Hero, HeroHistory, Item, ItemHistory, NPC, NPCHistory, Ability, AbilityHistory,
    Match, CompetitiveTeam, MatchDraft, MatchPlayer, MatchHeroMovement, MatchEvent,
    StagingReparseMatch
)
from darkseer.util import upsert, chunks
from typer import Argument as A_, Option as O_
import sqlalchemy as sa
import typer

from ._async import _coro
from ._ux import console, RichGroup, RichCommand
from .common import extra_options


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


def unique(duplicated):
    intermediary = {tuple(e.items()) for e in duplicated}
    return [dict(e) for e in intermediary]


async def write_matches(sess: AsyncSession, matches: List[schema.Match]):
    """
    """
    matches = [m.dict() for m in matches]
    deps = ('tournament', 'teams', 'accounts', 'draft', 'players', 'hero_movements', 'events')

    t = unique([m['tournament'] for m in matches if m['tournament'] is not None])
    for chunk in chunks(t, n=5000):
        stmt = upsert(Tournament).values(chunk)
        await sess.execute(stmt)

    c = unique([c for m in matches for c in m['teams']])
    for chunk in chunks(c, n=6000):
        stmt = upsert(CompetitiveTeam).values(chunk)
        await sess.execute(stmt)

    m = [{k: v for k, v in m.items() if k not in deps} for m in matches]
    for chunk in chunks(m, n=2500):
        stmt = upsert(Match).values(chunk)
        await sess.execute(stmt)

    a = unique([a for m in matches for a in m['accounts']])
    for chunk in chunks(a, n=10000):
        stmt = upsert(Account).values(chunk)
        await sess.execute(stmt)

    d = [d for m in matches for d in m['draft']]
    for chunk in chunks(d, n=5000):
        stmt = upsert(MatchDraft).values(chunk)
        await sess.execute(stmt)

    p = [p for m in matches for p in m['players']]
    for chunk in chunks(p, n=3000):
        stmt = upsert(MatchPlayer).values(chunk)
        await sess.execute(stmt)

    x = [x for m in matches for x in m['hero_movements']]
    for chunk in chunks(x, n=5000):
        stmt = upsert(MatchHeroMovement).values(chunk)
        await sess.execute(stmt)

    e = [e for m in matches for e in m['events']]
    for chunk in chunks(e, n=2500):
        stmt = upsert(MatchEvent).values(chunk)
        await sess.execute(stmt)


@app.command(cls=RichCommand)
@extra_options(database=True, rest=True)
@_coro
async def missing(
    **extra_options
):
    """
    Collect missing matches.
    """
    token = extra_options.pop('stratz_token')
    db = Database(**extra_options)

    with console.status('fetching missing matches from the darskeer database..') as status:
        async with db.session() as sess:
            stmt = sa.select(StagingReparseMatch.match_id)
            r = await sess.execute(stmt)
            match_ids = [match_id for match_id in r.scalars()]

    match_ids = match_ids[:21]

    async with Stratz(bearer_token=token) as api:
        s = 's' if len(match_ids) > 1 else ''

        with console.status(f'collecting data on {len(match_ids)} match id{s}..'):
            gathered = await asyncio.gather(*[
                api.matches(match_ids=chunk) for chunk in chunks(match_ids, n=10)
            ])
            r = [match for _ in gathered for match in _]
            matches = [_ for _ in r if isinstance(_, schema.Match)]
            incomplete = [_ for _ in r if isinstance(_, schema.IncompleteMatch)]

        with console.status(f'asking STRATZ to reparse {len(incomplete)} matches'):
            await api.reparse(replay_salts=[i.replay_salt for i in incomplete])

    with console.status('writing data to darskeer database..') as status:
        async with db.session() as sess:
            status.update(f'writing {len(matches)} matches to the darkseer database')
            await write_matches(sess, matches)

            status.update(f'deleting {len(matches)} matches from the stage')
            stmt = sa.delete(StagingReparseMatch).filter(StagingReparseMatch.match_id.in_([v.match_id for v in matches]))
            await sess.execute(stmt)

            status.update(f'writing {len(incomplete)} matches to the stage')
            print(incomplete)
            stmt = upsert(StagingReparseMatch).values([v.dict() for v in incomplete])
            await sess.execute(stmt)


@app.command(cls=RichCommand)
@extra_options(database=True, rest=True)
@_coro
async def pro_pubs(
    **extra_options
):
    """
    Collect Pro-level Pub matches.
    """
    extra_options.pop('stratz_token')
    db = Database(**extra_options)

    # MMR > 7000, Ranked, All Draft
    SQL = """
        SELECT match_id, start_time
          FROM public_matches
         WHERE avg_mmr >= 7000 AND game_mode = 22 AND lobby_type = 7 AND start_time >= 1625097600
         ORDER BY start_time DESC
    """

    with console.status('collecting data from OPENDOTA explorer..'):
        async with OpenDota() as api:
            r = await api.explorer(SQL)
            matches = [{'match_id': row['match_id'], 'replay_salt': 0} for row in r]

    with console.status('writing data to darskeer database..') as status:
        async with db.session() as sess:
            status.update(f'writing {len(matches)} matches to the stage')
            stmt = upsert(StagingReparseMatch).values(matches)
            await sess.execute(stmt)


@stratz_app.command(cls=RichCommand)
@extra_options(database=True, rest=True)
@_coro
async def patch(
    patch: str=O_(None, help='Specific patch to get data for.'),
    **extra_options
):
    """
    Collect Game Version data.
    """
    token = extra_options.pop('stratz_token')
    db = Database(**extra_options)

    with console.status('collecting data on patches..'):
        async with Stratz(bearer_token=token) as api:
            r = await api.patches()

    with console.status('writing data to darskeer database..'):
        async with db.session() as sess:
            stmt = upsert(GameVersion).values([v.dict() for v in r])
            await sess.execute(stmt)


@stratz_app.command(cls=RichCommand)
@extra_options(database=True, rest=True)
@_coro
async def tournament(
    matches: bool=O_(False, '--matches', help='Whether or not to grab matches.'),
    league_id: int=O_(None, help='Specific league to get data for.'),
    **extra_options
):
    """
    Collect Tournament data.
    """
    token = extra_options.pop('stratz_token')
    db = Database(**extra_options)

    async with Stratz(bearer_token=token) as api:
        with console.status('collecting data on tournaments..'):
            leagues = await api.tournaments()

            if league_id:
                leagues = [t for t in leagues if t.league_id == league_id]

        if matches:
            matches = []
            incomplete = []

            for league in leagues:
                with console.status(f'collecting matches for {league.league_name}..'):
                    m = await api.tournament_matches(league_id=league.league_id)
                    matches.extend(_ for _ in m if isinstance(_, schema.Match))
                    incomplete.extend(_ for _ in m if isinstance(_, schema.IncompleteMatch))

            with console.status(f'asking STRATZ to reparse {len(incomplete)} matches'):
                await api.reparse(replay_salts=[i.replay_salt for i in incomplete])

    with console.status('writing data to darskeer database..') as status:
        async with db.session() as sess:
            status.update(f'writing {len(leagues)} leagues to the darkseer database')
            stmt = upsert(Tournament).values([v.dict() for v in leagues])
            await sess.execute(stmt)

            if matches:
                status.update(f'writing {len(matches)} matches to the darkseer database')
                await write_matches(sess, matches)

                status.update(f'writing {len(incomplete)} matches to the stage')
                stmt = upsert(StagingReparseMatch).values([v.dict() for v in incomplete])
                await sess.execute(stmt)


@stratz_app.command(cls=RichCommand)
@extra_options(database=True, rest=True)
@_coro
async def match(
    match_id: List[int]=O_(None, help='Match ID to get data for.'),
    **extra_options
):
    """
    Collect Match data.
    """
    if not match_id:
        console.print('[error]must provide at least one match and/or tournament!')
        raise typer.Exit(-1)

    try:
        match_id = list(iter(match_id))
    except TypeError:
        match_id = [match_id]

    token = extra_options.pop('stratz_token')
    db = Database(**extra_options)

    async with Stratz(bearer_token=token) as api:
        s = 's' if len(match_id) > 1 else ''
        ids = ','.join(map(str, match_id))
        with console.status(f'collecting data on match id{s} {ids}..'):
            r = await api.matches(match_ids=match_id)
            matches = [_ for _ in r if isinstance(_, schema.Match)]
            incomplete = [_ for _ in r if isinstance(_, schema.IncompleteMatch)]

        with console.status(f'asking STRATZ to reparse {len(incomplete)} matches'):
            await api.reparse(replay_salts=[i.replay_salt for i in incomplete])

    with console.status('writing data to darskeer database..') as status:
        async with db.session() as sess:
            status.update(f'writing {len(matches)} matches to the darkseer database')
            await write_matches(sess, matches)

            status.update(f'writing {len(incomplete)} matches to the stage')
            stmt = upsert(StagingReparseMatch).values([v.dict() for v in incomplete])
            await sess.execute(stmt)


@stratz_app.command(cls=RichCommand)
@extra_options(database=True, rest=True)
@_coro
async def hero(
    patch: str=O_(None, help='Game Version of the Hero to get data for.'),
    since: bool=O_(False, '--since', help='Get data on all patches since.'),
    hero_id: str=O_(None, help='Specific Hero to get data for.'),
    **extra_options
):
    """
    Collect Hero history data.
    """
    token = extra_options.pop('stratz_token')
    db = Database(**extra_options)

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
@extra_options(database=True, rest=True)
@_coro
async def item(
    patch: str=O_(None, help='Game Version of the Hero to get data for.'),
    since: bool=O_(False, '--since', help='Get data on all patches since.'),
    item_id: str=O_(None, help='Specific Item to get data for.'),
    **extra_options
):
    """
    Collect Item history data.
    """
    token = extra_options.pop('stratz_token')
    db = Database(**extra_options)

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
@extra_options(database=True, rest=True)
@_coro
async def npc(
    patch: str=O_(None, help='Game Version of the Hero to get data for.'),
    since: bool=O_(False, '--since', help='Get data on all patches since.'),
    npc_id: str=O_(None, help='Specific NPC to get data for.'),
    **extra_options
):
    """
    Collect NPC history data.
    """
    token = extra_options.pop('stratz_token')
    db = Database(**extra_options)

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
@extra_options(database=True, rest=True)
@_coro
async def ability(
    patch: str=O_(None, help='Game Version of the Hero to get data for.'),
    since: bool=O_(False, '--since', help='Get data on all patches since.'),
    ability_id: str=O_(None, help='Specific Ability to get data for.'),
    **extra_options
):
    """
    Collect Ability history data.
    """
    token = extra_options.pop('stratz_token')
    db = Database(**extra_options)

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


@stratz_app.command(cls=RichCommand)
@extra_options(database=True, rest=True)
@_coro
async def setup_database(
    patch: str=O_('7.00', help='Game Version of the Hero to get data for.'),
    since: bool=O_(False, '--since', help='Get data on all patches since.'),
    **extra_options
):
    """
    Setup the Darkseer database.

    This command defaults to all dimensional data since patch 7.00, which includes:
      - Patches
      - Heroes
      - Items
      - Abilities
      - NPCs
      - Tournaments (all available from STRATZ)
    """
    token = extra_options.pop('stratz_token')
    db = Database(**extra_options)

    # 1. patches
    # 2. tournaments
    # 3. heroes
    # 4. items
    # 5. abilities
    # 6. npcs

    data = {
        'patch': {'model': GameVersion, 'data': []},
        'tournament': {'model': Tournament, 'data': []},
        'hero': {'model': Hero, 'data': []},
        'item': {'model': Item, 'data': []},
        'ability': {'model': Ability, 'data': []},
        'npc': {'model': NPC, 'data': []},
        'hero_history': {'model': HeroHistory, 'data': []},
        'item_history': {'model': ItemHistory, 'data': []},
        'ability_history': {'model': AbilityHistory, 'data': []},
        'npc_history': {'model': NPCHistory, 'data': []}
    }

    with console.status('collecting data..') as status:
        async with Stratz(bearer_token=token) as api:
            patches, tournaments = await asyncio.gather(
                api.patches(), api.tournaments()
            )

            data['patch']['data'] = patches
            data['tournament']['data'] = tournaments

            if patch:
                try:
                    cutoff = next(p for p in patches if p.patch == patch)
                except StopIteration:
                    console.print(f'[error]patch \'{patch}\' does not exist!')
                    raise typer.Exit(-1)

                if since:
                    patches = [p for p in patches if p.patch_id >= cutoff.patch_id]
                else:
                    patches = [p for p in patches if p.patch_id == cutoff.patch_id]

            for patch in patches:
                status.update(f'collecting history on {patch.patch}')
                hero_hist, item_hist, ability_hist, npc_hist = await asyncio.gather(
                    api.heroes(patch_id=patch.patch_id),
                    api.items(patch_id=patch.patch_id),
                    api.abilities(patch_id=patch.patch_id),
                    api.npcs(patch_id=patch.patch_id)
                )

                data['hero_history']['data'].extend(hero_hist)
                data['item_history']['data'].extend(item_hist)
                data['ability_history']['data'].extend(ability_hist)
                data['npc_history']['data'].extend(npc_hist)

                data['hero']['data'].extend([
                    h.to_hero() for h in hero_hist
                    if h.hero_id not in (_.hero_id for _ in data['hero']['data'])
                ])
                data['item']['data'].extend([
                    i.to_item() for i in item_hist
                    if i.item_id not in (_.item_id for _ in data['item']['data'])
                ])
                data['ability']['data'].extend([
                    a.to_ability() for a in ability_hist
                    if a.ability_id not in (_.ability_id for _ in data['ability']['data'])
                ])
                data['npc']['data'].extend([
                    n.to_npc() for n in npc_hist
                    if n.npc_id not in (_.npc_id for _ in data['npc']['data'])
                ])

    with console.status('writing data to darskeer database..') as status:
        async with db.session() as sess:
            for name, records in data.items():
                status.update(f'writing [yellow]{name}[/] data to darkseer database..')
                model = records['model']
                values = [v.dict() for v in records['data']]

                for chunk in chunks(values, n=1000):
                    stmt = upsert(model).values(chunk)
                    await sess.execute(stmt)
