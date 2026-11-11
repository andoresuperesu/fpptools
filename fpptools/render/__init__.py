"""Drawing and PDF output for `fpptools str sheet`. Needs matplotlib (`pip install fpptools[report]`).

Ported from the emmegisoft_fpp_customReports study tools; the verified FP rules (and the notes that explain
them) were kept as they were.
"""

from __future__ import annotations

from fpptools.errors import FppToolsError


def require_matplotlib() -> None:
    try:
        import matplotlib  # noqa: F401
    except ImportError as exc:
        raise FppToolsError("This command needs matplotlib: pip install fpptools[report]") from exc
