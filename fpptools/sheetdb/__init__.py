"""Phase 2 of `str sheet`: database readers, one module per section (SELECT only, via db.ReadOnlyDB).

`read_all(db, data)` runs them all for one style and returns a `SheetDb`. A failing database never stops the sheet:
the error is kept in `SheetDb.error` and the sections print "not resolved".
"""

from __future__ import annotations

from dataclasses import dataclass

from fpptools.errors import FppToolsError
from fpptools.sheet_data import SheetData
from fpptools.sheetdb.kits import KitsDb, read_kits
from fpptools.sheetdb.machinings import MachiningsDb, read_machinings
from fpptools.sheetdb.panes import PanesDb, read_panes
from fpptools.sheetdb.profiles import ProfilesDb, read_profiles


@dataclass
class SheetDb:
    profiles: ProfilesDb | None = None
    kits: KitsDb | None = None
    panes: PanesDb | None = None
    machinings: MachiningsDb | None = None
    error: str = ""           # database unreachable / unexpected failure: every db section is "not resolved"


def kit_fitting_codes(kits: KitsDb | None) -> dict[str, set[str]]:
    """Kit code -> every fitting code the kit can put on the job (fixed rows, their replacements, choice rows)."""
    out: dict[str, set[str]] = {}
    if kits is None:
        return out
    for code, kit in kits.kits.items():
        codes: set[str] = set()
        for row in list(kit.fixed) + [r for g in kit.choices for r in g.rows]:
            if row.code:
                codes.add(row.code)
            codes.update(r.code for r in row.replaced_by if r.code)
        out[code] = codes
    return out


def read_all(db, data: SheetData) -> SheetDb:
    """All database sections for one style. `db` is a db.ReadOnlyDB (or anything with .query(sql))."""
    res = SheetDb()
    try:
        res.profiles = read_profiles(db, data)
        res.kits = read_kits(db, data)
        rooms = {f"{p.series}\\{p.code}".casefold(): p.glazing_room
                 for p in (res.profiles.get(r.series, r.code) for r in data.profiles) if p is not None}
        res.panes = read_panes(db, data, room_by_profile=rooms)
        res.machinings = read_machinings(db, data, kit_fitting_codes(res.kits))
    except FppToolsError as exc:
        res.error = str(exc)
    except Exception as exc:  # a schema difference must not stop the PDF
        res.error = f"{type(exc).__name__}: {exc}"
    return res
