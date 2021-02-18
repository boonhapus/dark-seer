import pathlib
import enum

from typer import Option as Opt
from rich.progress import Progress
from rich import print
import sqlalchemy as sa
import typer

from darkseer.informants.stratz import StratzClient
from darkseer.informants.valve import ValveCDNClient

from _cli import coro


_app = typer.Typer()


class ImageType(str, enum.Enum):
    icon = 'icon'
    full = 'image'


@_app.command()
@coro
async def hero(imgtype: ImageType=Opt('icon', '--type', help='either icon or image')):
    """

    """
    _here = pathlib.Path(__file__)
    _dir = _here.parent.parent / f'darkseer/img/hero/{imgtype}'

    if not _dir.exists():
        _dir.mkdir(parents=True)

    print('\n    [b medium_purple1]Dark Seer[/]')
    print(f'[slate_blue1]{hero.__doc__}[/]\n')
    sz_api = StratzClient()
    va_api = ValveCDNClient()
    heroes = await sz_api.heroes()

    with Progress(transient=False) as bar:
        grab = bar.add_task('[red]Downloading..', total=len(heroes))
        save = bar.add_task('[red]Saving..', total=len(heroes))

        async for img in va_api.images(heroes, image_type=imgtype):
            bar.update(grab, advance=1)

            with open(_dir / f'{img.name}.png', mode='wb') as f:
                f.write(img.getbuffer())
                bar.update(save, advance=1)


if __name__ == '__main__':
    try:
        _app()
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
