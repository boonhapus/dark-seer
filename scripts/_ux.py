from typing import List
import re

from rich.default_styles import DEFAULT_STYLES
from rich.console import Console
from rich.theme import Theme
from click import Context, HelpFormatter
import click


RE_CLICK_SPECIFIER = re.compile(r'\[((?:default|required)(?:.+)?)\]')
CONSOLE_THEME = Theme({n: s.from_color() for n, s in DEFAULT_STYLES.items() if 'repr' in n})
console = Console(theme=CONSOLE_THEME)


def sort_options(params: List[str], *, default_prefix='~!'):
    """
    Sort command options in the help menu.

    Options:
      --options native to the command
      --default options
      --help

    Each set of options will be ordered as well, with required options being
    sent to the top of the list.
    """
    options = []
    default = []

    for option, help_text in params:
        if help_text.startswith(default_prefix):
            help_text = help_text[len(default_prefix):].lstrip()
            target = default
        else:
            target = options

        # rich and typer/click don't play nicely together.
        # - rich's color spec is square-braced
        # - click's default|required spec is square-braced
        #
        # if a command has a default or required option, rich thinks it's part
        # of the color spec and will swallow it. So we'll convert click's spec
        # from [] to () to fix that.
        if (matches := RE_CLICK_SPECIFIER.findall(help_text)):
            for match in matches:
                help_text = help_text.replace(f'[{match}]', f'[yellow]({match})[/]')

        to_add = (option, help_text)
        getattr(target, 'append')(to_add)

    return [*options, *default]


class RichGroup(click.Group):
    """
    """
    def get_help(self, ctx: Context) -> str:
        """
        Formats the help into a string and returns it.
        """
        formatter = ctx.make_formatter()
        self.format_help(ctx, formatter)
        return formatter.getvalue()

    def format_help(self, ctx: Context, formatter: HelpFormatter) -> None:
        """
        Writes the help into the formatter if it exists.
        """
        formatter.write('\n')
        self.format_usage(ctx, formatter)
        self.format_help_text(ctx, formatter)
        self.format_options(ctx, formatter)
        self.format_commands(ctx, formatter)
        self.format_epilog(ctx, formatter)

    def format_options(self, ctx, formatter):
        options = []

        for param in self.get_params(ctx):
            if (r := param.get_help_record(ctx)) is not None:
                options.append(r)

        if options:
            *params, help_ = options
            options = sort_options(params)

            with formatter.section('Options'):
                formatter.write_dl([
                    *options,
                    help_
                ])


class RichCommand(click.Command):
    """
    """
    def get_help(self, ctx: Context) -> str:
        """
        Formats the help into a string and returns it.
        """
        formatter = ctx.make_formatter()
        self.format_help(ctx, formatter)
        return formatter.getvalue()

    def format_help(self, ctx: Context, formatter: HelpFormatter) -> None:
        """
        Writes the help into the formatter if it exists.
        """
        self.format_usage(ctx, formatter)
        self.format_help_text(ctx, formatter)
        self.format_options(ctx, formatter)
        self.format_epilog(ctx, formatter)

    def format_options(self, ctx, formatter):
        options = []

        for param in self.get_params(ctx):
            if (r := param.get_help_record(ctx)) is not None:
                options.append(r)

        if options:
            *params, help_full, help_ = options
            options = sort_options(params)

            if '--helpfull' in click.get_os_args():
                options = [*options, help_]
            else:
                options = [*options, help_full, help_]

            with formatter.section('Options'):
                formatter.write_dl([*options])
