"""`fpptools wipe ...`: remove parts of structures/blocks. Simulates unless --apply."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable

import click
from lxml import etree

from fpptools import __version__, safe_write, strfile
from fpptools.app import App, pass_app
from fpptools.commands import scope_options

PANE = "8650"        # FP_NODE ElementType of a pane
GLASS_PIECE = "8510"  # FP_PIECE Type of a glass

Transform = Callable[[etree._ElementTree], list[str]]


def wipe_panedefs(tree) -> list[str]:
    """Remove glass fittings, glass DXF and pane table from every pane."""
    actions = []
    for pane in tree.iter("FP_NODE"):
        if pane.get("ElementType") != PANE:
            continue
        code = pane.get("Code", "?")
        for fit in [c for c in pane if c.tag == "FP_FITTING"]:
            pane.remove(fit)
            actions.append(f"pane {code}: glass fitting {fit.get('Code', '?')} removed")
        for piece in pane.iter("FP_PIECE"):
            if piece.get("Type") == GLASS_PIECE and "DXF" in piece.attrib:
                dxf = piece.attrib.pop("DXF")
                actions.append(f"pane {code}: glass DXF {dxf} removed")
        if "PaneTableCode" in pane.attrib:
            table = pane.attrib.pop("PaneTableCode")
            actions.append(f"pane {code}: pane table {table} removed")
    return actions


def wipe_kits(tree) -> list[str]:
    """Remove every kit."""
    actions = []
    for kit in list(tree.iter("FP_KIT")):
        kit.getparent().remove(kit)
        actions.append(f"kit {kit.get('Code', '?')} removed")
    return actions


def run(app: App, kind: str, title: str, transform: Transform, root, under, match, apply, backup_dir,
        report) -> None:
    base = app.root(kind, root)
    files = strfile.find_files(base, strfile.EXTENSIONS[kind], under, match)
    cs = safe_write.ChangeSet(base)
    with click.progressbar(files, label=f"Checking {kind.upper()} files", file=click.get_text_stream("stderr"),
                           show_pos=True) as bar:
        for f in bar:
            try:
                doc = strfile.parse(f)
            except etree.XMLSyntaxError as exc:
                click.echo(f"\nwarning: skipped {f}: {exc}", err=True)
                continue
            actions = transform(doc.tree)
            if actions:
                cs.add(safe_write.FileChange(f, strfile.serialize(doc), actions))
    header = (f"fpptools {__version__} wipe {title} - {datetime.now():%Y-%m-%d %H:%M}\n"
              f"Root: {base}" + (f"\nUnder: {under}" if under else "") + (f"\nMatch: {match}" if match else ""))
    if not cs.changes:
        click.echo(f"Nothing to change in {len(files)} file(s).")
        return
    if apply:
        dest = safe_write.apply(cs, backup_dir, header)
        lines = cs.report_lines(applied=True)
        click.echo("\n".join(lines))
        click.echo(f"Backup and report: {dest}")
    else:
        lines = [header, "", "SIMULATION - nothing was written.", ""] + cs.report_lines(applied=False)
        lines += ["", "Run again with --apply to write (originals are backed up first)."]
        click.echo("\n".join(lines))
        if report:
            Path(report).write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
            click.echo(f"Report: {report}")


def apply_options(f):
    f = click.option("--report", type=click.Path(dir_okay=False, path_type=Path),
                     help="Also save the simulation report to this file.")(f)
    f = click.option("--backup-dir", type=click.Path(file_okay=False, path_type=Path),
                     default=Path("fpptools_backups"), show_default=True,
                     help="Where --apply copies the originals (a timestamped subfolder is created).")(f)
    f = click.option("--apply", is_flag=True, help="Write the changes. Without it, only simulates.")(f)
    return f


@click.group("wipe")
def wipe_group():
    """Remove parts of structures/blocks. Simulates unless --apply is given."""


@wipe_group.command("panedefs")
@scope_options
@apply_options
@pass_app
def panedefs_cmd(app: App, root, under, match, apply, backup_dir, report):
    """Remove pane definitions from structures.

    From every pane: glass fittings, the glass DXF and the pane table code.
    Leaves a reusable base that cannot be used without re-checking glass and
    pane table.
    """
    run(app, "str", "panedefs", wipe_panedefs, root, under, match, apply, backup_dir, report)


@wipe_group.command("kits")
@click.option("--source", type=click.Choice(["str", "blk"]), default="str", show_default=True)
@scope_options
@apply_options
@pass_app
def kits_cmd(app: App, source, root, under, match, apply, backup_dir, report):
    """Remove every kit from structures or blocks."""
    run(app, source, "kits", wipe_kits, root, under, match, apply, backup_dir, report)
