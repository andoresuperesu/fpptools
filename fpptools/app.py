"""Shared CLI state passed to every command."""

from __future__ import annotations

from pathlib import Path

import click

from fpptools import config


class App:
    """The FP Pro configuration is loaded only when a command needs it."""

    def __init__(self, ini: Path | None):
        self._ini = ini
        self._cfg: config.FppConfig | None = None

    @property
    def cfg(self) -> config.FppConfig:
        if self._cfg is None:
            self._cfg = config.load(self._ini)
        return self._cfg

    def root(self, kind: str, override: Path | None) -> Path:
        return Path(override) if override else self.cfg.root_for(kind)


pass_app = click.make_pass_decorator(App)
