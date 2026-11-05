"""Backwards-compatible module path for fpptools <= 0.1.x (entry point was fpptools.fpptools:cli)."""

from fpptools.cli import cli, main

__all__ = ["cli", "main"]
