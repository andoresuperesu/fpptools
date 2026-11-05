"""Double-click launcher: export the structures of the active FP Pro configuration
to estructuras.xlsx next to the exe (same as `fpptools str list --lang es -o estructuras.xlsx`).

Built as fpptools_estructuras.exe by scripts/build_exe.ps1; also installed as the
`fpptools-estructuras` command.
"""

from __future__ import annotations

import sys
import traceback
from datetime import datetime
from pathlib import Path

import click

from fpptools.cli import cli

FILENAME = "estructuras.xlsx"


def output_folder() -> Path:
    """Folder of the exe when frozen; current folder otherwise."""
    return Path(sys.executable).parent if getattr(sys, "frozen", False) else Path.cwd()


def target_file(folder: Path) -> Path:
    """estructuras.xlsx, or a timestamped name if that file is open in Excel."""
    out = folder / FILENAME
    try:
        if out.exists():
            with open(out, "r+b"):
                pass
        return out
    except PermissionError:
        return folder / f"estructuras_{datetime.now():%Y%m%d_%H%M%S}.xlsx"


def run(folder: Path) -> int:
    out = target_file(folder)
    click.echo("fpptools - exportar estructuras de la configuración activa de FP Pro\n")
    try:
        cli.main(args=["str", "list", "--lang", "es", "-o", str(out)], prog_name="fpptools",
                 standalone_mode=False)
    except click.ClickException as exc:
        exc.show()
        return 1
    except OSError as exc:
        click.echo(f"\nNo se pudo escribir {out}: {exc}\n"
                   "Copie el programa a una carpeta donde tenga permisos de escritura.", err=True)
        return 1
    except Exception:  # unexpected: show it, the window stays open
        traceback.print_exc()
        return 1
    click.echo(f"\nListo: {out}")
    return 0


def main() -> None:
    code = run(output_folder())
    if sys.stdin is not None and sys.stdin.isatty():  # double-clicked: keep the window open
        try:
            input("\nPulse Enter para cerrar...")
        except EOFError:
            pass
    sys.exit(code)


if __name__ == "__main__":
    main()
