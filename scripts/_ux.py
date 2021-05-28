from gettext import gettext as _

from rich.console import Console
import click


console = Console(force_terminal=True)


class RichGroup(click.Group):
    """
    """
    def format_usage(self, ctx, formatter):
        pieces = ' '.join(self.collect_usage_pieces(ctx))

        with console.capture() as cap:
            console.print(f'[green]Usage[/]: {ctx.command_path} {pieces}')

        formatter.write(cap.get())

    def format_help_text(self, ctx, formatter):
        text = self.help or ""

        if self.deprecated:
            text = _("(Deprecated) {text}").format(text=text)

        if text:
            formatter.write_paragraph()

            with console.capture() as cap:
                console.print(f'[yellow]{text}[/]')

            with formatter.indentation():
                formatter.write(cap.get())

    def format_options(self, ctx, formatter):
        required_common_opts = []
        common_opts = []
        opts = []

        for param in self.get_params(ctx):
            r = param.get_help_record(ctx)

            if r is None:
                continue

            *pre, help_ = r

            if help_.startswith('~! '):
                r = tuple([*pre, help_[3:]])

                if help_.endswith('[required]'):
                    required_common_opts.append(r)
                else:
                    common_opts.append(r)

                continue

            opts.append(r)

        if opts:
            *opts, help_opt = opts

            with formatter.section(_("Options")):
                formatter.write_dl([
                    *opts,
                    *required_common_opts,
                    *common_opts,
                    help_opt
                ])


class RichCommand(click.Command):
    """
    """
    def format_usage(self, ctx, formatter):
        pieces = ' '.join(self.collect_usage_pieces(ctx))

        with console.capture() as cap:
            console.print(f'[green]Usage[/]: {ctx.command_path} {pieces}')

        formatter.write(cap.get())

    def format_help_text(self, ctx, formatter):
        text = self.help or ""

        if self.deprecated:
            text = _("(Deprecated) {text}").format(text=text)

        if text:
            formatter.write_paragraph()

            with console.capture() as cap:
                console.print(f'[yellow]{text}[/]')

            with formatter.indentation():
                formatter.write(cap.get())

    def format_options(self, ctx, formatter):
        required_common_opts = []
        common_opts = []
        opts = []

        for param in self.get_params(ctx):
            r = param.get_help_record(ctx)

            if r is None:
                continue

            *pre, help_ = r

            if help_.startswith('~! '):
                r = tuple([*pre, help_[3:]])

                if help_.endswith('[required]'):
                    required_common_opts.append(r)
                else:
                    common_opts.append(r)

                continue

            opts.append(r)

        if opts:
            *opts, help_opt = opts

            with formatter.section(_("Options")):
                formatter.write_dl([
                    *opts,
                    *required_common_opts,
                    *common_opts,
                    help_opt
                ])
