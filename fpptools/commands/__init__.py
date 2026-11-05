"""CLI command groups. Shared options live here."""

from __future__ import annotations

from pathlib import Path

import click

HEADERS = {
    "en": {"folder": "Folder", "name": "Name", "unique": "Unique code", "description": "Description",
           "file": "File", "fitting": "Fitting", "source": "Source", "note": "Note", "error": "Error",
           "job": "Job", "item": "Item"},
    "es": {"folder": "Carpeta", "name": "Nombre", "unique": "Nombre único", "description": "Descripción",
           "file": "Archivo", "fitting": "Accesorio", "source": "Origen", "note": "Nota", "error": "Error",
           "job": "Trabajo", "item": "Ítem"},
}


def scope_options(f):
    """--root / --under / --match, shared by every command that walks STR/BLK folders."""
    f = click.option("--match", metavar="PATTERN",
                     help="Only files whose name (no extension) matches, e.g. 'VTA_*'. Case-insensitive.")(f)
    f = click.option("--under", metavar="FOLDER",
                     help="Only inside this folder, relative to the root, e.g. '019_SERIE_22_PESADO'.")(f)
    f = click.option("--root", type=click.Path(file_okay=False, exists=True, path_type=Path),
                     help="Folder to scan instead of the one in FP_PRO.INI.")(f)
    return f


def lang_option(f):
    return click.option("--lang", type=click.Choice(["en", "es"]), default="en", show_default=True,
                        help="Language of the column headers.")(f)


def out_option(default: str):
    return click.option("--out", "-o", default=default, show_default=True,
                        help="Output file (.csv or .xlsx), or '-' for the console.")
