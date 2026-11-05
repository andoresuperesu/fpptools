"""`fpptools fit ...`: fittings used in structures, blocks and jobs."""

from __future__ import annotations

import os
from pathlib import Path

import click
from lxml import etree

from fpptools import db as dbmod
from fpptools import strfile
from fpptools.app import App, pass_app
from fpptools.commands import HEADERS, lang_option, scope_options
from fpptools.errors import FppToolsError
from fpptools.output import write_table

JOBRECORD = "_JOBRECORD"


def _origin(el) -> str:
    parent = el.getparent()
    return f"{parent.tag}:{parent.get('Code', '')}" if parent is not None else ""


def fittings_in_design(path: Path, kits: dict[str, list[str]] | None) -> list[tuple[str, str, str]]:
    """(fitting code, source, note) for one STR/BLK. Kits are expanded from the database."""
    tree = etree.parse(str(path), etree.XMLParser(resolve_entities=False, huge_tree=True))
    rows = []
    for fit in tree.iter("FP_FITTING"):
        parent = fit.getparent()
        if parent is not None and parent.tag == "FP_KIT":
            continue  # kit content comes from the database
        rows.append((fit.get("Code", ""), _origin(fit), ""))
    for kit in tree.iter("FP_KIT"):
        name = kit.get("Code", "")
        if kits is None:
            rows.append(("", f"FP_KIT:{name}", "kit not expanded (--no-db)"))
        elif name in kits:
            rows.extend((code, f"FP_KIT:{name}", "") for code in kits[name])
        else:
            rows.append(("", f"FP_KIT:{name}", "kit not found in database"))
    return rows


def job_files(root: Path, job: str | None) -> list[Path]:
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort(key=str.casefold)
        for name in sorted(filenames, key=str.casefold):
            upper = name.upper()
            if not upper.endswith(".XML") or JOBRECORD not in upper:
                continue
            if job and not upper.startswith(job.upper() + JOBRECORD):
                continue
            found.append(Path(dirpath) / name)
    return found


def job_and_item(path: Path) -> tuple[str, str]:
    stem = path.stem
    job, _, rest = stem.upper().partition(JOBRECORD)
    item = stem[len(job) + len(JOBRECORD):].lstrip("_") or stem[-2:]
    return stem[: len(job)], item


@click.group("fit")
def fit_group():
    """Fittings (accessories)."""


@fit_group.command("list")
@click.option("--source", type=click.Choice(["str", "blk", "job", "jobs"]), default="str", show_default=True,
              help="Structures, blocks, one job (--job) or all jobs.")
@click.option("--job", metavar="NAME", help="Job name for --source job (asked if missing).")
@click.option("--no-db", is_flag=True, help="Do not read the database; kits are listed but not expanded.")
@scope_options
@click.option("--out", "-o", default=None, help="Output file (.csv or .xlsx), or '-' for the console. "
              "[default: fittings_<source>.csv]")
@lang_option
@pass_app
def fit_list(app: App, source: str, job: str | None, no_db: bool, root: Path | None, under: str | None,
             match: str | None, out: str | None, lang: str):
    """List the fittings used in structures, blocks or job records.

    Fittings inside kits are taken from the database (kit / dettagliokit).
    """
    h = HEADERS[lang]
    out = out or f"fittings_{source}.csv"
    rows: list[list[str]] = []
    if source in ("job", "jobs"):
        if source == "job" and not job:
            job = click.prompt("Job name")
        base = app.root("job", root)
        files = job_files(base, job if source == "job" else None)
        if not files:
            raise FppToolsError(f"No job records found in {base}" + (f" for job {job}" if job else ""))
        headers = [h["job"], h["item"], h["fitting"], h["source"]]
        for f in files:
            j, item = job_and_item(f)
            tree = etree.parse(str(f), etree.XMLParser(resolve_entities=False, huge_tree=True))
            rows.extend([j, item, el.get("Code", ""), _origin(el)] for el in tree.iter("FP_FITTING"))
    else:
        base = app.root(source, root)
        files = strfile.find_files(base, strfile.EXTENSIONS[source], under, match)
        kits = None
        if not no_db:
            database = dbmod.ReadOnlyDB(app.cfg)
            try:
                kits = dbmod.kit_fittings(database)
            finally:
                database.close()
        headers = [h["folder"], h["file"], h["fitting"], h["source"], h["note"]]
        with click.progressbar(files, label=f"Reading {source.upper()} files",
                               file=click.get_text_stream("stderr"), show_pos=True) as bar:
            for f in bar:
                folder = strfile.rel_folder(f, base)
                try:
                    found = fittings_in_design(f, kits)
                except etree.XMLSyntaxError as exc:
                    click.echo(f"\nwarning: {f}: cannot read: {exc}", err=True)
                    rows.append([folder, f.name, "", "", f"cannot read: {exc}"])
                    continue
                rows.extend([folder, f.name, code, src, note] for code, src, note in found)
    where = write_table(headers, rows, out)
    click.echo(f"{len(rows)} row(s) from {len(files)} file(s) -> {where}", err=True)


@click.command("list_fittings", hidden=True)
@click.option("--searchtype", type=click.Choice(["str", "blk", "job", "jobs"]), default="str")
@click.option("--tofile", type=bool, default=True)
@click.option("--verbose", type=bool, default=False)
@click.pass_context
def legacy_list_fittings(ctx: click.Context, searchtype: str, tofile: bool, verbose: bool):
    """fpptools 0.1 syntax; use `fpptools fit list`."""
    click.echo("note: list_fittings is deprecated, use `fpptools fit list`.", err=True)
    if tofile:
        ctx.invoke(fit_list, source=searchtype, out=f"fittinglist_{searchtype}.csv")
    if verbose or not tofile:
        ctx.invoke(fit_list, source=searchtype, out="-")
