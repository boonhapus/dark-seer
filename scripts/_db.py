from inspect import Signature, Parameter
from typing import List

from darkseer.database import Database
from darkseer.models import *
from typer import Argument as A_, Option as O_
import typer

from ._async import _coro
from ._ux import RichGroup, RichCommand


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


app = typer.Typer(
    help='Perform database functions.',
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
    tables: List[str]=O_(None, help='Subset of tables to create'),
    recreate: bool=O_(False, '--recreate', help='drop all tables prior to creating'),
    **db_options
):
    """
    Create tables in the data model.
    """
    db = Database(**db_options)

    async with db.engine.begin() as cnxn:
        if recreate:
            await cnxn.run_sync(db.metadata.drop_all)

        await cnxn.run_sync(db.metadata.create_all)#, tables=tables)


@app.command(cls=RichCommand)
@db_options
@_coro
async def drop(
    tables: List[str]=O_(None, help='Subset of tables to drop'),
    **db_options
):
    """
    Drop tables in the data model.
    """
    db = Database(**db_options)

    async with db.engine.begin() as cnxn:
        r = await cnxn.run_sync(db.metadata.drop_all, tables=tables)
        print(r)


@app.command(cls=RichCommand)
@db_options
@_coro
async def truncate(
    tables: List[str]=O_(None, help='Subset of tables to truncate'),
    **db_options
):
    """
    Truncate one, many, or all tables in the data model.
    """
    db = Database(**db_options)

    # async with db.engine.begin() as cnxn:
    #     r = await cnxn.run_sync(db.metadata.drop_all, tables=tables)


@app.command(cls=RichCommand)
@db_options
@_coro
async def export(
    table: str=A_(..., help='Table to export'),
    where: str=O_(None, help='Optional filter clause to add to the data pull'),
    **db_options
):
    """
    Extract data from a specific table.
    """
    db = Database(**db_options)

    async with db.session() as sess:
        pass


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
