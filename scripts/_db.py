from typing import List
import pathlib

from darkseer.database import Database
# from darkseer.models import *
from typer import Argument as A_, Option as O_
import typer
import sqlalchemy as sa

from ._async import _coro
from ._ux import console, RichGroup, RichCommand
from .common import extra_options, _csv


app = typer.Typer(
    help="""
    Interact with the database backend.
    """,
    cls=RichGroup
)


@app.command(cls=RichCommand, hidden=True)
@extra_options(database=True)
@_coro
async def interactive(
    **extra_options
):
    """
    Connect an interactive session to the database.
    """
    db = Database(**extra_options)
    # do interactive stuff here


@app.command(cls=RichCommand)
@extra_options(database=True)
@_coro
async def create(
    tables_: List[str]=O_(None, '--tables', help='Subset of tables to create', callback=_csv),
    recreate: bool=O_(False, '--recreate', help='drop all tables prior to creating'),
    **extra_options
):
    """
    Create tables in the data model.
    """
    db = Database(**extra_options)
    tables = [t for t in db.metadata.sorted_tables if t.name in (tables_ or db.tables)]
    names  = ', '.join([t.name for t in tables]) if tables_ else 'all tables'

    async with db.engine.begin() as cnxn:
        if recreate:
            console.print(f'[red]dropping[/]: {names}')
            await cnxn.run_sync(db.metadata.drop_all, tables=tables)

        console.print(f'[green]creating[/]: {names}')
        await cnxn.run_sync(db.metadata.create_all, tables=tables)


@app.command(cls=RichCommand)
@extra_options(database=True)
@_coro
async def drop(
    tables_: List[str]=O_(None, '--tables', help='Subset of tables to drop'),
    **extra_options
):
    """
    Drop tables in the data model.
    """
    db = Database(**extra_options)
    tables = [t for t in db.metadata.sorted_tables if t.name in (tables_ or db.tables)]
    names  = ', '.join([t.name for t in tables]) if tables_ else 'all tables'

    async with db.engine.begin() as cnxn:
        console.print(f'[red]dropping[/]: {names}')
        await cnxn.run_sync(db.metadata.drop_all, tables=tables)


@app.command(cls=RichCommand)
@extra_options(database=True)
@_coro
async def truncate(
    tables_: List[str]=O_(None, '--tables', help='Subset of tables to truncate'),
    **extra_options
):
    """
    Truncate one, many, or all tables in the data model.
    """
    db = Database(**extra_options)
    tables = [t for t in db.metadata.sorted_tables if t.name in (tables_ or db.tables)]

    async with db.session() as sess:
        for table in tables:
            console.print(f'[warning]truncating[/]: {table.name}')
            await sess.execute(table.delete())


@app.command(cls=RichCommand)
@extra_options(database=True)
@_coro
async def export(
    tablename: str=A_(..., help='Table to export.'),
    save_path: pathlib.Path=A_(..., help='Directory to save ouput.'),
    where: str=O_(None, help='Optional filter clause to add to the data pull.'),
    **extra_options
):
    """
    Extract data from a specific table.
    """
    db = Database(**extra_options)

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
@extra_options(database=True)
@_coro
async def query(
    sql: str=A_(..., help='Statement to execute'),
    **extra_options
):
    """
    Extract data from a specific table.
    """
    db = Database(**extra_options)

    async with db.session() as sess:
        await sess.execute(sql)
