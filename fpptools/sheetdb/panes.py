"""Section 4 of `str sheet`: pane tables (rellenados) of a style. SELECT only, through db.ReadOnlyDB.

Facts (vault FPProMySQLSchema/11, checked on the DESA database):
- A glazing node's `PaneTableCode` (GUID) is `riempimenti.codice`; `riempimenti.descrizione` is the name FP shows.
- `serieprofiloriempimenti` lists the profile series (by name) that may use a table.
- `combinazioniriempimenti`: one row per glass thickness (`spessorevetro`) and room (`spazioutile`), with up to four
  beads `codicefermavetro..4` written 'SERIES|CODE'; `accessoririempimenti` holds the fittings of a combination
  (same three key columns).
- `spazioutile` = the glazing room = `profili.spazio_utile` of the profile around the glass.
- The glass DXF of an 8510 piece (e.g. GLASSES\\06MM) is a drawing, not a `vetri` row: the glass actually used is
  chosen in the job, so the thickness is NOT read from the DXF name.

The sheet's "surrounding profile" is not known per opening (SheetData keeps no parent link), so the room is taken
from every non-bead profile of the style with a room > 0; `rooms_resolved` says whether that worked. When it did not,
nothing is filtered by room and `rooms_resolved` is False (the sheet then prints 'not resolved').

SQL is plain (single-table SELECT with literals, joins in Python) so it runs on MySQL and Access alike.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fpptools.sheet_data import SheetData

BEAD_USES = ("8180", "8270")   # glazing bead / panel bead: their own room is not the glass room
_CHUNK = 100
_ROOM_EPS = 0.01


@dataclass
class PaneFitting:
    type: str            # accessoririempimenti.tipo (raw code)
    code: str
    description: str
    qty: float | None    # num_base
    default: bool        # predefinito


@dataclass
class PaneCombo:
    thickness: float | None     # spessorevetro
    room: float | None          # spazioutile
    beads: list[str]            # 'SERIES\\CODE', up to 4
    tolerance: float | None
    fittings: list[PaneFitting] = field(default_factory=list)


@dataclass
class PaneTable:
    code: str                   # riempimenti.codice (GUID)
    name: str
    tolerance: float | None     # riempimenti.tolleranza (glass thickness tolerance)
    series: list[str] = field(default_factory=list)
    combos: list[PaneCombo] = field(default_factory=list)     # already filtered by room when rooms_resolved


@dataclass
class PaneOpening:
    openings: list[str]         # node codes, as in SheetData.panes
    glass: str                  # glass DXF stem in the style
    beads: str                  # beads in the style, as read from the STR
    pane_table_code: str
    table: PaneTable | None     # None = no code in the style, or not found in the database


@dataclass
class PanesDb:
    openings: list[PaneOpening] = field(default_factory=list)
    rooms: dict[str, float] = field(default_factory=dict)     # 'SERIES\\CODE' -> room used for filtering
    rooms_resolved: bool = False
    could_apply: list[PaneTable] = field(default_factory=list)   # other tables for the style's series and rooms
    notes: list[str] = field(default_factory=list)


def _lit(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _in(values) -> str:
    return "(" + ", ".join(_lit(v) for v in values) + ")"


def _chunks(items: list[str]):
    for i in range(0, len(items), _CHUNK):
        yield items[i:i + _CHUNK]


def _num(v) -> float | None:
    try:
        return None if v is None else float(v)
    except (TypeError, ValueError):
        return None


def _bead(code: str) -> str:
    return code.replace("|", "\\")


def _profile_rooms(db, data: SheetData) -> dict[str, float]:
    """'SERIES\\CODE' (original case) -> spazio_utile > 0, for the style's non-bead profiles."""
    wanted = {(p.series.casefold(), p.code.casefold()): f"{p.series}\\{p.code}"
              for p in data.profiles if p.use not in BEAD_USES and p.use != "8510"}
    if not wanted:
        return {}
    series_of = {int(r[0]): str(r[1]) for r in db.query("SELECT pkid, serie FROM serie_profili")}
    out: dict[str, float] = {}
    for part in _chunks([p.code for p in data.profiles if p.use not in BEAD_USES]):
        for serieid, codice, room in db.query(
                "SELECT serieid, codice, spazio_utile FROM profili WHERE codice IN " + _in(part)):
            key = (series_of.get(int(serieid), "").casefold(), str(codice).casefold())
            r = _num(room)
            if key in wanted and r and r > 0:
                out[wanted[key]] = r
    return out


def _room_ok(room: float | None, rooms: list[float]) -> bool:
    return room is not None and any(abs(room - r) <= _ROOM_EPS for r in rooms)


def read_panes(db, data: SheetData, room_by_profile: dict[str, float | None] | None = None) -> PanesDb:
    """Resolve the style's pane tables and list the ones that could apply (see module docstring).

    room_by_profile: optional 'SERIES\\CODE' (case-insensitive) -> room, replacing the database lookup."""
    result = PanesDb()
    if room_by_profile is not None:
        rooms = {k: float(v) for k, v in room_by_profile.items() if v}
    else:
        rooms = _profile_rooms(db, data)
    result.rooms = rooms
    result.rooms_resolved = bool(rooms)
    room_values = sorted(set(rooms.values()))
    if not result.rooms_resolved:
        result.notes.append("rooms_not_resolved")

    names = {str(c): (str(n), _num(t)) for c, n, t in db.query("SELECT codice, descrizione, tolleranza FROM riempimenti")}
    series_by_table: dict[str, list[str]] = {}
    for code, serie in db.query("SELECT codiceriempimento, serieprofilo FROM serieprofiloriempimenti"):
        series_by_table.setdefault(str(code), []).append(str(serie))

    style_series = {p.series.casefold() for p in data.profiles if p.series}
    style_codes = [pn.pane_table for pn in data.panes if pn.pane_table]
    candidate = [c for c, s in series_by_table.items()
                 if any(x.casefold() in style_series for x in s) and c not in style_codes and c in names]
    wanted_codes = sorted(set(style_codes) | set(candidate))

    combos: dict[str, list[PaneCombo]] = {}
    keyed: dict[tuple[str, float | None, float | None], PaneCombo] = {}
    for part in _chunks(wanted_codes):
        for row in db.query(
                "SELECT codiceriempimento, spessorevetro, spazioutile, codicefermavetro, codicefermavetro2, "
                "codicefermavetro3, codicefermavetro4, tolleranza FROM combinazioniriempimenti "
                "WHERE codiceriempimento IN " + _in(part)):
            code, thick, room, b1, b2, b3, b4, tol = row
            c = PaneCombo(_num(thick), _num(room), [_bead(str(b)) for b in (b1, b2, b3, b4) if b], _num(tol))
            combos.setdefault(str(code), []).append(c)
            keyed[(str(code), c.thickness, c.room)] = c
        for row in db.query(
                "SELECT codiceriempimento, spessorevetro, spazioutile, tipo, codice, descr, num_base, predefinito "
                "FROM accessoririempimenti WHERE codiceriempimento IN " + _in(part)):
            code, thick, room, tipo, fcode, descr, qty, default = row
            c = keyed.get((str(code), _num(thick), _num(room)))
            if c is not None:
                c.fittings.append(PaneFitting(str(tipo), str(fcode), str(descr or ""), _num(qty), bool(default)))

    def table(code: str) -> PaneTable:
        name, tol = names[code]
        cs = combos.get(code, [])
        if result.rooms_resolved:
            cs = [c for c in cs if _room_ok(c.room, room_values)]
        cs = sorted(cs, key=lambda c: (c.thickness if c.thickness is not None else -1, c.room or 0))
        return PaneTable(code, name, tol, sorted(series_by_table.get(code, [])), cs)

    for pn in data.panes:
        t = table(pn.pane_table) if pn.pane_table in names else None
        if pn.pane_table and t is None:
            result.notes.append(f"pane table {pn.pane_table} not found")
        result.openings.append(PaneOpening(list(pn.openings), pn.glass, pn.beads, pn.pane_table, t))

    if result.rooms_resolved:
        others = [table(c) for c in candidate]
        result.could_apply = sorted((t for t in others if t.combos), key=lambda t: t.name.casefold())
    return result
