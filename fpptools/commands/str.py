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


@str_group.command("sheet")
@scope_options
@click.option("--out", "-o", default="str_sheets.pdf", show_default=True, help="Output PDF.")
@click.option("--page", type=click.Choice(["letter"]), default="letter", show_default=True,
              help="Paper size (landscape).")
@click.option("--sight", type=click.Choice(["int", "ext"]),
              help="Draw the elevation as seen from inside or outside (mirrors when the style was drawn "
                   "for the other side). Default: as stored in the style.")
@click.option("--no-db", is_flag=True, help="Do not read the database (profile descriptions, kit contents, "
              "fixings, pane tables, machinings): faster, files only.")
@lang_option
@pass_app
def str_sheet(app: App, root: Path | None, under: str | None, match: str | None, out: str, page: str,
              sight: str | None, no_db: bool, lang: str):
    """One PDF page per structure: elevation plus what the library applies to it.

    Read-only (files and database). Needs matplotlib: pip install fpptools[report]. Elevation, profile use,
    kit list, glazing fittings and multijoint (NOD) fittings come from the files; descriptions, kit contents,
    fixings, pane tables and machinings from the database (skip with --no-db).

    \b
    Examples:
      fpptools str sheet --under DESA_DOORS --match "100-*" -o doors.pdf
      fpptools str sheet --match "VTA_X*" --sight ext --lang es
    """
    from datetime import date

    from fpptools import __version__, sheet_data, sheetdb
    from fpptools.db import ReadOnlyDB
    from fpptools.render import require_matplotlib

    require_matplotlib()
    from fpptools.render import sheet as sheet_pdf

    base = app.root("str", root)
    cfg = app.cfg
    files = strfile.find_files(base, strfile.EXTENSIONS["str"], under, match)
    if not files:
        raise click.ClickException("No structures match.")
    items = []
    db = None if no_db else ReadOnlyDB(cfg)
    try:
        with click.progressbar(files, label="Reading structures", file=click.get_text_stream("stderr"),
                               show_pos=True) as bar:
            for f in bar:
                data = sheet_data.read_sheet(f, base, cfg.nodes_path)
                if db is not None and not data.error:
                    data.db = sheetdb.read_all(db, data)
                items.append((data, f.read_bytes().decode(strfile.ENCODING, errors="replace")))
    finally:
        if db is not None:
            db.close()
    failed = next((d.db.error for d, _ in items if d.db is not None and d.db.error), "")
    if failed:
        click.echo(f"warning: database sections not resolved: {failed}", err=True)
    prm = cfg.prm_path
    sheet_pdf.write_pdf(items, out, prm_dir=prm if prm and prm.is_dir() else None, sight=sight, lang=lang,
                        config_name=cfg.name, date=date.today().isoformat(), version=__version__)
    click.echo(f"{len(items)} sheet(s) from {base} -> {out}", err=True)


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
