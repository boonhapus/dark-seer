from enum import Enum
import pathlib

from rich.prompt import Confirm, Prompt
from rich import print
import sqlalchemy as sa
import typer
import toml

from darkseer.database import Database
from darkseer.models import *


def _drop_everything(engine: sa.engine.Engine) -> None:
    """
    Utility function to CASCADE DROP all tables.

    Drops all foreign key constraints before dropping all tables.
    Workaround for SQLAlchemy not doing DROP ## CASCADE for drop_all()

    Further reading:
      https://github.com/pallets/flask-sqlalchemy/issues/722
    """
    from sqlalchemy.engine.reflection import Inspector
    from sqlalchemy.schema import (
        DropConstraint,
        DropTable,
        MetaData,
        Table,
        ForeignKeyConstraint,
    )

    with engine.connect() as cnxn:
        inspector = Inspector.from_engine(engine)

        # We need to re-create a minimal metadata with only the required things
        # to successfully emit drop constraints and tables commands for
        # postgres (based on the actual schema of the running instance)
        meta = MetaData()
        tables = []
        all_fk = []

        for table_name in inspector.get_table_names():
            fks = []

            for fk in inspector.get_foreign_keys(table_name):
                if not fk['name']:
                    continue

                fks.append(ForeignKeyConstraint((), (), name=fk["name"]))

            tables.append(Table(table_name, meta, *fks))
            all_fk.extend(fks)

        for fk in all_fk:
            cnxn.execute(DropConstraint(fk))

        for table in tables:
            cnxn.execute(DropTable(table))


#
#
#


@sa.event.listens_for(sa.engine.Engine, 'after_cursor_execute')
def _receive_after_drop(cnxn, cur, statement, *a, **kw):
    """
    Listen for DROP TABLE events and emit a pretty log.
    """
    cmd = 'DROP TABLE '

    if cmd in statement:
        print(f'[red]DROP TABLE[/]: {statement[len(cmd) + 1:]}')


@sa.event.listens_for(sa.Table, 'after_create')
def _receive_after_create(target, connection, **kw):
    """
    Listen for CREATE TABLE events and emit a pretty log.
    """
    print(f'[green]CREATE TABLE[/]: {target}')


class DBDialect(str, Enum):
    postgresql = 'postgresql'
    mysql = 'mysql'
    sqlite = 'sqlite'

    @classmethod
    def to_list(cls) -> list:
        return [member.value for role, member in cls.__members__.items()]


def app(
    dialect: DBDialect=typer.Option(None, help='database dialect'),
    username: str=typer.Option(None, help='authentication username'),
    password: str=typer.Option(None, hide_input=True, help='authentication password'),
    host: str=typer.Option(None, help='hostname of the machine where the database is located'),
    drop: bool=typer.Option(None, '--drop', help='whether or not to drop all tables prior to creating'),
    config: pathlib.Path=typer.Option(None, '--toml', is_eager=True, help='configuration file in lieu of arguments'),
):
    """
    create_database.py

    Creates the Dark Seer database schema.
    """
    print('\n    [b medium_purple1]Dark Seer[/]')
    print(f'[slate_blue1]{app.__doc__}[/]\n')

    if config is not None:
        data = toml.load(config)
        dialect  = data['database'].get('dialect', None)
        username = data['database'].get('username', None)
        password = data['database'].get('password', None)
        host     = data['database'].get('host', None)
    else:
        typer.echo('Configuration file not specified, defining arguments interactively..')

    if dialect is None:
        dialect = Prompt.ask('[-] Choose database dialect', choices=DBDialect.to_list(), default='postgresql')

    if username is None:
        username = Prompt.ask('[-] Username')

    if password is None:
        password = Prompt.ask('[-] Password', password=True, default='None')

    passwd = f':{password}' if password not in [None, 'None'] else ''

    if host is None:
        host = Prompt.ask('[-] Host')

    if drop is None:
        drop = Confirm.ask('[-] Should we refresh the database?')

    print()

    #
    # Configuration of app is done.
    #

    db = Database(f'{dialect}://{username}{passwd}@{host}/darkseer')

    if drop:
        _drop_everything(db._engine)

    db._metadata.create_all(db._engine)


if __name__ == '__main__':
    try:
        typer.run(app)
    except sa.exc.OperationalError as e:
        err_stmt, *_ = str(e.orig).split('\n')
        _, msg = err_stmt.split(': ')
        msg = f'Database error: {msg.strip()}'
    except FileNotFoundError as e:
        msg = f'Config file error: {e.args[-1]} "{e.filename}"'
    else:
        raise SystemExit(0)

    print('\n:-(\nSomething went wrong\n')
    print(f'[bold red]{msg}[/]')
    print('\n[yellow]Having trouble? Use [green]--help[/] to learn what arguments are acceptable.[/]')
