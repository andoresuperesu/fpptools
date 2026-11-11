"""Profiles of a style from the database: description, compound components, glazing room, fixings.

Join keys (FPProMySQLSchema/10, checked on a Desa MySQL 8 archive):
- a profile is `serie_profili.serie` + `profili.codice`; `profili.serieid` -> `serie_profili.pkid`. The series name
  is the DXF folder of the STR piece (`DESA_DOORS\\C2515HP_JAMB.DXF`); kits write it with a space ("DESA DOORS"), so
  both spellings are tried.
- compounds: `profili.composto` = 1; components in `profilicomponenti` (`profcompostoid` -> `profcomponenteid`),
  `master` = 1 marks the main component. The same component can appear on several rows (counted).
- fixings: `fissaggi.idprof`; `tipo` 1 = a fitting (`idacc` -> `accessori.pkid`), 10 = a profile used instead of a
  fitting (`idacc` -> `profili.pkid`). `lung` = cut length, `num_base` = base quantity (the formula columns that
  can change it are NOT evaluated, so the quantity is the base one). Compounds use the fixings of their main
  (master) profile; a compound without a master gets none and a note (not guessed).

Portable SQL only (MySQL and Access): plain joins, IN lists, no parameters (the drivers disagree on placeholders:
literals are escaped here), no recursion (done in Python). Never reads `fp_utenti`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fpptools.sheet_data import SheetData

CHUNK = 400   # IN-list size (Access limits statement length)


@dataclass
class Component:
    series: str
    code: str
    description: str
    master: bool
    count: int = 1          # rows with this component in the compound


@dataclass
class Fixing:
    kind: str               # "fitting" | "profile" | "unknown" (fissaggi.tipo 1 | 10 | other)
    series: str             # "" when not resolved
    code: str               # "" when not resolved (the referenced row is missing)
    description: str
    qty: int | None         # base quantity (num_base)
    cut_length: float | None    # lung (0 = none)
    max_qty: int | None     # num_max (0 = no limit)
    optional: bool
    use: str                # utilizzo, "" when none
    from_profile: str = ""  # main profile code when the profile is a compound


@dataclass
class ProfileDb:
    series: str             # as written in the STR (DXF folder)
    code: str
    found: bool             # a profili row exists
    description: str = ""
    compound: bool = False
    components: list[Component] = field(default_factory=list)
    glazing_room: float | None = None    # profili.spazio_utile (None = NULL; 0 = not defined)
    fixings: list[Fixing] = field(default_factory=list)
    fixings_note: str = ""  # why fixings are empty when it is not simply "none"


@dataclass
class ProfilesDb:
    profiles: dict[tuple[str, str], ProfileDb] = field(default_factory=dict)   # key (series, code) casefolded
    notes: list[str] = field(default_factory=list)

    def get(self, series: str, code: str) -> ProfileDb | None:
        return self.profiles.get((series.casefold(), code.casefold()))


# -- helpers ---------------------------------------------------------------------

def _lit(s: str) -> str:
    return "'" + str(s).replace("'", "''") + "'"


def _chunks(items, n=CHUNK):
    items = list(items)
    for i in range(0, len(items), n):
        yield items[i:i + n]


def _in(col: str, items, quote: bool) -> str:
    return f"{col} IN (" + ", ".join(_lit(i) if quote else str(int(i)) for i in items) + ")"


def _f(v) -> float | None:
    return None if v is None else float(v)


def _i(v) -> int | None:
    return None if v is None else int(v)


def _s(v) -> str:
    return "" if v is None else str(v).strip()


# -- reader ----------------------------------------------------------------------

def read_profiles(db, data: SheetData) -> ProfilesDb:
    """Database facts for every profile of `data.profiles`. `db` needs `.query(sql)` (db.ReadOnlyDB)."""
    out = ProfilesDb()
    wanted = {(p.series.casefold(), p.code.casefold()): (p.series, p.code) for p in data.profiles}
    if not wanted:
        return out

    # series: try the DXF spelling and the space spelling
    names = {}
    for series, _ in wanted.values():
        for variant in {series, series.replace("_", " ")}:
            names[variant.casefold()] = variant
    series_id: dict[str, int] = {}      # casefolded DB series name -> pkid
    for chunk in _chunks(sorted(set(names.values()))):
        for pkid, serie in db.query(f"SELECT pkid, serie FROM serie_profili WHERE {_in('serie', chunk, True)}"):
            series_id[_s(serie).casefold()] = int(pkid)

    def sid(series: str) -> int | None:
        return series_id.get(series.casefold()) or series_id.get(series.replace("_", " ").casefold())

    by_series: dict[int, set[str]] = {}
    for series, code in wanted.values():
        s = sid(series)
        if s is not None:
            by_series.setdefault(s, set()).add(code)

    rows: dict[tuple[int, str], tuple] = {}     # (series pkid, code casefold) -> db row
    for s, codes in by_series.items():
        for chunk in _chunks(sorted(codes)):
            for r in db.query("SELECT pkid, codice, descr, composto, spazio_utile FROM profili "
                              f"WHERE serieid = {int(s)} AND {_in('codice', chunk, True)}"):
                rows[(s, _s(r[1]).casefold())] = r

    # compounds: components
    comp_ids = [int(r[0]) for r in rows.values() if r[3]]
    comps: dict[int, list[tuple[int, bool]]] = {}   # compound pkid -> [(component pkid, master)]
    for chunk in _chunks(comp_ids):
        for cid, part, master in db.query("SELECT profcompostoid, profcomponenteid, master FROM profilicomponenti "
                                          f"WHERE {_in('profcompostoid', chunk, False)} ORDER BY pkid"):
            comps.setdefault(int(cid), []).append((int(part), bool(master)))

    # fixings: of the profile, or of the main component for compounds
    fix_owner: dict[int, int | None] = {}   # profile pkid -> pkid whose fixings apply
    for r in rows.values():
        pkid = int(r[0])
        if r[3]:
            masters = [p for p, m in comps.get(pkid, []) if m]
            fix_owner[pkid] = masters[0] if masters else None
        else:
            fix_owner[pkid] = pkid
    owners = sorted({o for o in fix_owner.values() if o is not None})
    fix_rows: dict[int, list[tuple]] = {}
    for chunk in _chunks(owners):
        for r in db.query("SELECT idprof, idacc, tipo, lung, num_base, num_max, opzionale, utilizzo FROM fissaggi "
                          f"WHERE {_in('idprof', chunk, False)} ORDER BY pkid"):
            fix_rows.setdefault(int(r[0]), []).append(r)

    # referenced rows: profiles (components, tipo 10 fixings) and fittings (tipo 1)
    prof_ref = {p for cl in comps.values() for p, _ in cl}
    acc_ref: set[int] = set()
    for rl in fix_rows.values():
        for r in rl:
            if r[1] is None:
                continue
            (prof_ref if int(r[2]) == 10 else acc_ref).add(int(r[1]))
    prof_info: dict[int, tuple[str, str, str]] = {}     # pkid -> (series, code, description)
    for chunk in _chunks(sorted(prof_ref | set(owners))):
        for pkid, serie, codice, descr in db.query(
                "SELECT p.pkid, s.serie, p.codice, p.descr FROM profili p "
                f"INNER JOIN serie_profili s ON s.pkid = p.serieid WHERE {_in('p.pkid', chunk, False)}"):
            prof_info[int(pkid)] = (_s(serie), _s(codice), _s(descr))
    acc_info: dict[int, tuple[str, str, str]] = {}
    for chunk in _chunks(sorted(acc_ref)):
        for pkid, serie, codice, descr in db.query(
                "SELECT a.pkid, sa.serie, a.codice, a.descr FROM accessori a "
                f"LEFT JOIN serie_accessori sa ON sa.pkid = a.serieid WHERE {_in('a.pkid', chunk, False)}"):
            acc_info[int(pkid)] = (_s(serie), _s(codice), _s(descr))

    def fixing(r, from_profile: str) -> Fixing:
        tipo = int(r[2]) if r[2] is not None else -1
        kind = {1: "fitting", 10: "profile"}.get(tipo, "unknown")
        info = None
        if r[1] is not None and kind == "fitting":
            info = acc_info.get(int(r[1]))
        elif r[1] is not None and kind == "profile":
            info = prof_info.get(int(r[1]))
        series, code, descr = info or ("", "", "")
        return Fixing(kind, series, code, descr, _i(r[4]), _f(r[3]), _i(r[5]), bool(r[6]), _s(r[7]), from_profile)

    for key, (series, code) in wanted.items():
        s = sid(series)
        r = rows.get((s, code.casefold())) if s is not None else None
        if r is None:
            out.profiles[key] = ProfileDb(series, code, False)
            continue
        pkid = int(r[0])
        p = ProfileDb(series, code, True, _s(r[2]), bool(r[3]), glazing_room=_f(r[4]))
        if p.compound:
            counted: dict[int, Component] = {}
            for part, master in comps.get(pkid, []):
                if part in counted:
                    counted[part].count += 1
                    counted[part].master = counted[part].master or master
                    continue
                ps, pc, pd = prof_info.get(part, ("", "", ""))
                counted[part] = Component(ps, pc, pd, master)
            p.components = list(counted.values())
        owner = fix_owner[pkid]
        if owner is None:
            p.fixings_note = "compound without a main profile" if p.compound else ""
        else:
            from_profile = "" if owner == pkid else prof_info.get(owner, ("", "", ""))[1]
            p.fixings = [fixing(fr, from_profile) for fr in fix_rows.get(owner, [])]
        out.profiles[key] = p
    return out
