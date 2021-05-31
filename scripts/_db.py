from inspect import Signature, Parameter
from typing import List, Tuple
import itertools as it
import pathlib

from darkseer.database import Database
from darkseer.models import *
from typer import Argument as A_, Option as O_
from click import Context, Parameter as Param
import typer
import sqlalchemy as sa

from ._async import _coro
from ._ux import console, RichGroup, RichCommand


def db_options(f):
    """
    Common options across all database commands.

    Common options will have their help command prefixed with the
    identifier ~! .. this will signify to the help parser that these
    opts should be processed and listed last.
    """
    param_info = {
        'echo': {
            'type': bool,
            'arg': O_(
                False, '--echo', help='~! Print database debug text.',
                envvar='DARKSEER_DATABASE_ECHO', show_envvar=False
            )
        },
        'host': {
            'type': str,
            'arg': O_(
                ..., help='~! URL where darkseer database lives.', prompt=True,
                envvar='DARKSEER_DATABASE_HOST', show_envvar=False
            )
        },
        'port': {
            'type': int,
            'arg': O_(
                None, help='~! Database port.', hidden=True,
                envvar='DARKSEER_DATABASE_PORT', show_envvar=False
            )
        },
        'username': {
            'type': str,
            'arg': O_(
                None, help='~! Authentication username.', hidden=True,
                envvar='DARKSEER_DATABASE_USERNAME', show_envvar=False
            )
        },
        'password': {
            'type': str,
            'arg': O_(
                None, help='~! Authentication password.', hidden=True,
                envvar='DARKSEER_DATABASE_PASSWORD', show_envvar=False
            )
        }
    }

    params = [
        Parameter(n, kind=Parameter.KEYWORD_ONLY, default=i['arg'], annotation=i['type'])
        for n, i in param_info.items()
    ]

    # construct a signature from f, add additional arguments.
    orig = Signature.from_callable(f)
    args = [p for n, p in orig.parameters.items() if n != 'db_options']
    sig = orig.replace(parameters=(*args, *params))
    f.__signature__ = sig
    return f


def _csv(ctx: Context, param: Param, value: Tuple[str]) -> List[str]:
    """
    Convert arguments to a list of strings.

    Arguments can be supplied on the CLI like..

      --tables table1,table2 --tables table3

    ..and will output as a flattened list of strings.

      ['table1', 'table2', 'table3']
    """
    return list(it.chain.from_iterable([v.split(',') for v in value]))


app = typer.Typer(
    help="""
    Interact with the database backend.
    """,
    cls=RichGroup
)


@app.command(cls=RichCommand)
@db_options
@_coro
async def interactive(
    **db_options
):
    """
    Connect an interactive session to the database.
    """
    db = Database(**db_options)
    # do interactive stuff here


@app.command(cls=RichCommand)
@db_options
@_coro
async def create(
    tables_: List[str]=O_(None, '--tables', help='Subset of tables to create', callback=_csv),
    recreate: bool=O_(False, '--recreate', help='drop all tables prior to creating'),
    **db_options
):
    """
    Create tables in the data model.
    """
    db = Database(**db_options)
    tables = [t for t in db.metadata.sorted_tables if t.name in (tables_ or db.tables)]
    names  = ', '.join([t.name for t in tables]) if tables_ else 'all tables'

    async with db.engine.begin() as cnxn:
        if recreate:
            console.print(f'[red]dropping[/]: {names}')
            await cnxn.run_sync(db.metadata.drop_all, tables=tables)

        console.print(f'[green]creating[/]: {names}')
        await cnxn.run_sync(db.metadata.create_all, tables=tables)


@app.command(cls=RichCommand)
@db_options
@_coro
async def drop(
    tables_: List[str]=O_(None, '--tables', help='Subset of tables to drop'),
    **db_options
):
    """
    Drop tables in the data model.
    """
    db = Database(**db_options)
    tables = [t for t in db.metadata.sorted_tables if t.name in (tables_ or db.tables)]
    names  = ', '.join([t.name for t in tables]) if tables_ else 'all tables'

    async with db.engine.begin() as cnxn:
        console.print(f'[red]dropping[/]: {names}')
        await cnxn.run_sync(db.metadata.drop_all, tables=tables)


@app.command(cls=RichCommand)
@db_options
@_coro
async def truncate(
    tables_: List[str]=O_(None, '--tables', help='Subset of tables to truncate'),
    **db_options
):
    """
    Truncate one, many, or all tables in the data model.
    """
    db = Database(**db_options)
    tables = [t for t in db.metadata.sorted_tables if t.name in (tables_ or db.tables)]

    async with db.session() as sess:
        for table in tables:
            console.print(f'[warning]truncating[/]: {table.name}')
            await sess.execute(table.delete())


@app.command(cls=RichCommand)
@db_options
@_coro
async def export(
    tablename: str=A_(..., help='Table to export.'),
    save_path: pathlib.Path=A_(..., help='Directory to save ouput.'),
    where: str=O_(None, help='Optional filter clause to add to the data pull.'),
    **db_options
):
    """
    Extract data from a specific table.
    """
    db = Database(**db_options)

    try:
        table = next((t for t in db.metadata.sorted_tables if t.name == tablename))
    except StopIteration:
        console.print(f'[error]table \'{tablename}\' does not exist!')
        raise typer.Exit(-1)

    async with db.session() as sess:
        q = sa.select(table)

        if where is not None:
            q = q.filter(sa.text(where))

        rows = await sess.execute(q)
        print([r for r in rows])


@app.command(cls=RichCommand, hidden=True)
@db_options
@_coro
async def query(
    sql: str=A_(..., help='Statement to execute'),
    **db_options
):
    """
    Extract data from a specific table.
    """
    db = Database(**db_options)

    async with db.session() as sess:
        await sess.execute(sql)
