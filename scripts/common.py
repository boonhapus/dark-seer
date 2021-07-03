from inspect import Signature, Parameter
from typing import List, Tuple, Callable
import itertools as it

from click import Context, Parameter as Param
from typer import Argument as A_, Option as O_


def _csv(ctx: Context, param: Param, value: Tuple[str]) -> List[str]:
    """
    Convert arguments to a list of strings.

    Arguments can be supplied on the CLI like..

      --tables table1,table2 --tables table3

    ..and will output as a flattened list of strings.

      ['table1', 'table2', 'table3']
    """
    return list(it.chain.from_iterable([v.split(',') for v in value]))


def db_options(f: Callable) -> Callable:
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
    args = [p for n, p in orig.parameters.items() if n != 'extra_options']
    sig = orig.replace(parameters=(*args, *params))
    f.__signature__ = sig
    return f


def api_options(f: Callable) -> Callable:
    """
    Common options across various REST-API commands.

    Common options will have their help command prefixed with the
    identifier ~! .. this will signify to the help parser that these
    opts should be processed and listed last.
    """
    param_info = {
        'stratz_token': {
            'type': str,
            'arg': O_(
                None, help='~! STRATZ Bearer token for elevated requests permission.',
                envvar='DARKSEER_STRATZ_TOKEN', show_envvar=False
            )
        },
    }

    params = [
        Parameter(n, kind=Parameter.KEYWORD_ONLY, default=i['arg'], annotation=i['type'])
        for n, i in param_info.items()
    ]

    # construct a signature from f, add additional arguments.
    orig = Signature.from_callable(f)
    args = [p for n, p in orig.parameters.items() if n != 'extra_options']
    sig = orig.replace(parameters=(*args, *params))
    f.__signature__ = sig
    return f


def extra_options(f: Callable=None, *, database: bool=False, rest: bool=False) -> Callable:
    """
    """
    import functools as ft

    # print(f, database)

    if f is None:
        return ft.partial(extra_options, database=database, rest=rest)

    if database:
        f = db_options(f)

    if rest:
        f = api_options(f)

    return f
