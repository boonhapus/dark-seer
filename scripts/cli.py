import darkseer
import typer

from ._data import app as data_app
from ._db import app as db_app
from ._ux import RichGroup


app = typer.Typer(
    help="""
    Welcome to Dark Seer!
    """,
    cls=RichGroup,
    add_completion=False,
    context_settings={'max_content_width': 125}
)


def run():
    """
    Entrypoint into dark-seer.
    """
    app.add_typer(data_app, name='data')
    app.add_typer(db_app, name='db')
    app(prog_name='darkseer')
