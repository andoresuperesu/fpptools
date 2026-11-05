"""`fpptools str ...`: structures (.STR) of the active configuration."""

from __future__ import annotations

from pathlib import Path

import click

from fpptools import strfile
from fpptools.app import App, pass_app
from fpptools.commands import HEADERS, lang_option, out_option, scope_options
from fpptools.output import write_table


@click.group("str")
def str_group():
    """Structures (.STR files)."""


@str_group.command("list")
@scope_options
@out_option("structures.csv")
@lang_option
@pass_app
def str_list(app: App, root: Path | None, under: str | None, match: str | None, out: str, lang: str):
    """List structures with folder, name, unique code and description.

    Same data as FP Pro's structure browser: Name is the file name,
    Unique code is NameStr, Description is the full description.

    \b
    Examples:
      fpptools str list
      fpptools str list --under 019_SERIE_22_PESADO --lang es -o serie22.xlsx
    """
    base = app.root("str", root)
    files = strfile.find_files(base, strfile.EXTENSIONS["str"], under, match)
    infos = []
    with click.progressbar(files, label="Reading structures", file=click.get_text_stream("stderr"),
                           show_pos=True) as bar:
        for f in bar:
            infos.append(strfile.read_info(f, base))
    errors = [i for i in infos if i.error]
    h = HEADERS[lang]
    headers = [h["folder"], h["name"], h["unique"], h["description"]]
    rows = [[i.folder, i.name, i.unique_code, i.description] for i in infos]
    if errors:
        headers.append(h["error"])
        for row, i in zip(rows, infos):
            row.append(i.error)
        for i in errors:
            click.echo(f"warning: {i.path}: {i.error}", err=True)
    where = write_table(headers, rows, out)
    click.echo(f"{len(infos)} structure(s) from {base} -> {where}"
               + (f" ({len(errors)} with errors)" if errors else ""), err=True)
