"""fpptools command line: `fpptools <group> <command>`.

Groups: config, str, fit, wipe. Run `fpptools <group> --help` for details.
"""

from __future__ import annotations

from pathlib import Path

import click

from fpptools import __version__, config
from fpptools.app import App
from fpptools.commands import config_cmd, fit, str as str_cmd, wipe


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="fpptools")
@click.option("--ini", type=click.Path(dir_okay=False, path_type=Path), envvar=config.ENV_INI,
              help="FP_PRO.INI to use. Default: the configuration FP Pro is using now.")
@click.pass_context
def cli(ctx: click.Context, ini: Path | None):
    """Administration and debugging tools for emmegisoft FP Pro.

    Works on the configuration currently active in FP Pro (FP_PRO.INI).
    """
    ctx.obj = App(ini)


cli.add_command(config_cmd.config_show)
cli.add_command(str_cmd.str_group)
cli.add_command(fit.fit_group)
cli.add_command(fit.legacy_list_fittings)
cli.add_command(wipe.wipe_group)


def main():
    cli(prog_name="fpptools")
