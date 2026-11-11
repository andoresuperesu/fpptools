"""Section 5 of the style sheet: EasyMac machinings that apply to the profiles of a style.

Sources (vault FPProMySQLSchema/16, columns checked on a real FP Pro 11 MySQL archive):
- `ldtaccessori`: one row per machining. Profiles are named by series + code (`serieprofilo1/codiceprofilo1` ..
  up to 4), each with its LDT file (`ldt`..`ldt4`); `macchina` = machine; `marca/serie/codice` = the fitting that
  triggers it; `tipolav` = the EasyMac tab (see TIPOLAV_NAMES).
- `profcompatldt`: special-code profiles that reuse the LDT machinings of a base profile.

Matching: a style profile (DXF folder = series, DXF stem = code, e.g. DESA_DOORS\\100BEV) is the same profile as
the DB row when series and code are equal, case-insensitive (checked on the DESA door library). Rows are listed
when ANY of their profiles is in the style; the profiles that are not in the style are reported separately, because a
hinge row names the sash and its frame partner and the partner may belong to another series.

Nothing is expanded through `profcompatldt` base profiles (whether a special-code profile inherits the base
profile's `ldtaccessori` rows is not verified): the compat rows are only reported.

No query parameters are used (MySQL and Access write placeholders differently): the two tables are read whole
(columns listed, no `*`) and filtered in Python. Never touches fp_utenti.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fpptools.sheet_data import SheetData

# `ldtaccessori.tipolav` -> EasyMac tab (vault FPProMySQLSchema/16, from the 11.0 query files). Unknown: "".
TIPOLAV_NAMES = {
    1: "Frame fixing", 2: "Handle", 3: "Drainage", 4: "Corner joints", 5: "Adjustable blocks", 6: "Hinges",
    7: "Locks", 8: "Side cut", 9: "Ventilation", 10: "Locking point", 11: "Central overlap",
    12: "Reinforcement", 13: "Side arm", 99: "Others", 100: "Facade mullion anchors",
    101: "Facade pre-fixing", 102: "Facade drain sheet", 103: "Facade fixing", 105: "Facade drainage",
    106: "Unitised anchors", 107: "Facade others for unit",
}

LDT_SQL = (
    "SELECT serieprofilo1, codiceprofilo1, serieprofilo2, codiceprofilo2, serieprofilo3, codiceprofilo3, "
    "serieprofilo4, codiceprofilo4, ldt, ldt2, ldt3, ldt4, macchina, marca, serie, codice, tipolav, "
    "descrizione, disabled FROM ldtaccessori"
)
COMPAT_SQL = "SELECT macchina, ldt, serie, codice, seriebase, codicebase FROM profcompatldt"


@dataclass
class MachiningRow:
    machine: str
    ldts: list[str]                 # LDT files, in profile order (empty and 'EMPTY' values dropped)
    kind_code: int | None           # ldtaccessori.tipolav
    kind: str                       # TIPOLAV_NAMES text, "" when unknown
    fitting: str                    # triggering fitting code ('' when the row has none)
    fitting_source: str         # "brand / series" of that fitting (marca / serie)
    description: str
    disabled: bool
    profiles_in_style: list[str]    # "SERIES\\CODE" of the row's profiles that are in the style
    profiles_not_in_style: list[str]
    # Does the style carry the triggering fitting?  None = unknown (no kit data given or the row has no fitting)
    in_style_kits: bool | None
    kits: list[str] = field(default_factory=list)   # the style's kits that contain the fitting (needs a dict)


@dataclass
class CompatRow:
    machine: str
    ldt: str
    profile: str                    # "SERIES\\CODE" (in the style)
    base_profile: str               # "SERIES\\CODE" whose machinings it reuses


@dataclass
class MachiningsDb:
    machinings: list[MachiningRow] = field(default_factory=list)
    compat: list[CompatRow] = field(default_factory=list)
    resolved: bool = True           # False: a query failed; see note
    note: str = ""


def _s(v) -> str:
    return "" if v is None else str(v).strip()


def _key(series: str, code: str) -> str:
    return f"{series}\\{code}".casefold()


def _ldt(v: str) -> bool:
    return bool(v) and v.upper() != "EMPTY"


def read_machinings(db, data: SheetData,
                    style_fitting_codes: set[str] | dict[str, set[str]] | None = None) -> MachiningsDb:
    """`db` = db.ReadOnlyDB (or anything with .query(sql)). `style_fitting_codes`: fitting codes the style's kits
    contain, either a set, or {kit code: set of fitting codes} to also name the kits that carry the fitting."""
    style = {_key(p.series, p.code): f"{p.series}\\{p.code}" for p in data.profiles if p.series and p.code}
    out = MachiningsDb()
    if not style:
        return out

    kit_of: dict[str, list[str]] = {}
    all_codes: set[str] | None = None
    if isinstance(style_fitting_codes, dict):
        all_codes = set()
        for kit, codes in style_fitting_codes.items():
            for c in codes:
                kit_of.setdefault(c.casefold(), []).append(kit)
                all_codes.add(c.casefold())
    elif style_fitting_codes is not None:
        all_codes = {c.casefold() for c in style_fitting_codes}

    try:
        rows = db.query(LDT_SQL)
    except Exception as exc:  # DB/driver error: the sheet prints "not resolved", never a guess
        out.resolved = False
        out.note = f"ldtaccessori: {exc}"
        rows = []
    for r in rows:
        r = [_s(v) for v in r]
        profs = [(r[i], r[i + 1], r[8 + i // 2]) for i in range(0, 8, 2) if r[i] and r[i + 1]]
        inside = list(dict.fromkeys(f"{s}\\{c}" for s, c, _ in profs if _key(s, c) in style))
        if not inside:
            continue
        outside = list(dict.fromkeys(f"{s}\\{c}" for s, c, _ in profs if _key(s, c) not in style))
        fitting = r[15]
        in_kits = None if (all_codes is None or not fitting) else fitting.casefold() in all_codes
        try:
            kind_code = int(float(r[16])) if r[16] else None
        except ValueError:
            kind_code = None
        out.machinings.append(MachiningRow(
            machine=r[12], ldts=[x for x in r[8:12] if _ldt(x)], kind_code=kind_code,
            kind=TIPOLAV_NAMES.get(kind_code, ""), fitting=fitting,
            fitting_source=" / ".join(x for x in (r[13], r[14]) if x), description=r[17],
            disabled=r[18] not in ("", "0", "False"), profiles_in_style=inside, profiles_not_in_style=outside,
            in_style_kits=in_kits, kits=kit_of.get(fitting.casefold(), []) if in_kits else []))
    out.machinings.sort(key=lambda m: (m.machine.casefold(), m.kind_code if m.kind_code is not None else 1000,
                                       m.fitting.casefold(), m.profiles_in_style))

    try:
        crows = db.query(COMPAT_SQL)
    except Exception as exc:
        out.resolved = False
        out.note = (out.note + "; " if out.note else "") + f"profcompatldt: {exc}"
        crows = []
    for mac, ldt, serie, codice, sbase, cbase in crows:
        mac, ldt, serie, codice, sbase, cbase = (_s(x) for x in (mac, ldt, serie, codice, sbase, cbase))
        if _key(serie, codice) in style:
            out.compat.append(CompatRow(mac, ldt, f"{serie}\\{codice}", f"{sbase}\\{cbase}"))
    out.compat.sort(key=lambda c: (c.machine.casefold(), c.profile.casefold(), c.ldt.casefold()))
    return out
