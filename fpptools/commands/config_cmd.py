"""`fpptools config`: show which FP Pro configuration fpptools will use."""

from __future__ import annotations

import click

from fpptools.app import App, pass_app


@click.command("config")
@pass_app
def config_show(app: App):
    """Show the active FP Pro configuration (password hidden)."""
    cfg = app.cfg

    def line(label: str, value) -> None:
        click.echo(f"{label:<16}{value}")

    def folder(key: str) -> str:
        value = cfg.get("SYSTEM", key)
        if not value:
            return "(not set)"
        from pathlib import Path
        return f"{value}" + ("" if Path(value).is_dir() else "   [not found]")

    line("INI", cfg.ini_path)
    line("Configuration", cfg.name or "(unknown)")
    line("STR_PATH", folder("STR_PATH"))
    line("BLK_PATH", folder("BLK_PATH"))
    line("JOB_PATH", folder("JOB_PATH"))
    line("CONFIGS_PATH", folder("CONFIGS_PATH"))
    if cfg.db_kind == "mysql":
        s = cfg.mysql
        line("Database", f"MySQL {s.host}:{s.port}/{s.database} (user {s.user}, charset {s.charset})")
    else:
        line("Database", f"Access {cfg.mdb_file}" + ("" if cfg.mdb_file.is_file() else "   [not found]"))
