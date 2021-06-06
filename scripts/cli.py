import logging

from rich.logging import RichHandler
import sqlalchemy as sa
import darkseer
import typer

from ._data import app as data_app
from ._db import app as db_app
from ._ux import console, RichGroup


log = logging.getLogger(__name__)
app = typer.Typer(
    help="""
    Welcome to Dark Seer!
    """,
    cls=RichGroup,
    add_completion=False,
    no_args_is_help=True,
    context_settings={'max_content_width': 125}
)


def run():
    """
    Entrypoint into dark-seer.
    """
    logging.basicConfig(
        level='DEBUG', format='%(message)s', datefmt='[%X]',
        handlers=[RichHandler(console=console, rich_tracebacks=True, markup=True)]
    )

    app.add_typer(data_app, name='data')
    app.add_typer(db_app, name='db')

    try:
        # console.print('\n\t[b medium_purple1]Dark Seer[/]')
        app(prog_name='darkseer')
    except sa.exc.OperationalError as e:
        err_stmt, *_ = str(e.orig).split('\n')
        _, msg = err_stmt.split(': ')
        msg = f'Database error: {msg.strip()}'
    except Exception as e:
        log.exception('uh-oh!')
        msg = f'{e}'
    else:
        raise typer.Exit()

    console.print(
        f'\n:-('
        f'\nSomething went wrong!'
        f'\n'
        f'\n[error]{msg}[/]'
    )
