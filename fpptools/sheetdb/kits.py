"""Section 2 (Kits), phase 2: what the kits of a style contain, read from the FP Pro database.

Pure: a `ReadOnlyDB`-like object (anything with `.query(sql) -> list[tuple]`) and a SheetData in, plain dataclasses
out. SELECT only, no query parameters (MySQL uses %s, Access ?), no CTEs and no MySQL-only syntax: joins are done in
Python. Nothing is guessed: a kit or fitting that cannot be found keeps `found=False` and the sheet prints
"not resolved".

Schema notes: vault FPProMySQLSchema/02 (kits), 04 (fittings, child fittings).
- A kit is found by group + name: FP_KIT@Serie = gruppikit.gruppo, FP_KIT@Code = kit.nomekit. Both are read from the
  STR file itself (SheetData.kits has no Serie); without a Serie in the STR the name must be unique.
- dettagliokit rows: tipo 1-4 fittings (10 profile, 11 glass, 12 panel); opzionale=1 is a choice row of the
  collection gruppoid (gruppiopzkit), defflg=1 its default; ranges (dim_rif + lim_inf/lim_sup) are size rules.
- accessori.fittizio: 0 real, 1 fictitious (EasyMac machining trigger), 2 warning, 3 error.
  accessori.sostituisci=1 with child rows (accessoricollegati): the BOM shows the children, recursively.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from fpptools.sheet_data import SheetData

MAX_DEPTH = 8          # replacement chains are short in practice; a cycle or runaway chain stops here
CHUNK = 200

# dim_rif codes seen in the data (vault 02: the program interprets them, they cannot be mapped from SQL).
# Anything else is shown as "ref <n>", never named.
DIM_REF_LABELS = {1: "H", 101: "O1"}


# -- result ---------------------------------------------------------------------------

@dataclass
class SizeRule:
    ref: int            # dim_rif code
    label: str          # "H", "O1" (width of sash 1), or "ref <n>" when the code is not known
    lo: float           # mm (database units)
    hi: float


@dataclass
class Resolved:
    """A fitting after replacement: what the BOM really lists."""
    code: str
    series: str
    description: str
    qty: float
    kind: str           # hardware | machining | fictitious | warning | error | unknown


@dataclass
class KitRowDb:
    tipo: int                         # 1-4 fitting, 10 profile, 11 glass, 12 panel
    code: str
    series: str                       # fitting series name ("" for non-fitting rows)
    description: str
    qty: float                        # num_base
    kind: str                         # hardware | machining | fictitious | warning | error | profile | glass | panel | unknown
    optional: bool                    # dettagliokit.opzionale (a choice)
    default: bool                     # defflg = 1
    group_id: int                     # collection id (gruppiopzkit), 0 = none
    dim_calc: int                     # 0 fixed count, 1 H, 2 W, 3 perimeter, 4 2H+L, 5 formula (quantity is length based)
    hand: str                         # "LH" | "RH" | "" (both)
    rules: list[SizeRule] = field(default_factory=list)   # size ranges, in database units (mm)
    more_ranges: bool = False         # ranges 3-8 are used too: not shown
    found: bool = True                # fitting row found in `accessori` (fittings only)
    replaced_by: list[Resolved] = field(default_factory=list)   # final hardware when the fitting is replaced


@dataclass
class ChoiceGroup:
    group_id: int
    name: str                         # gruppiopzkit.descrizione, "" when none
    rows: list[KitRowDb] = field(default_factory=list)

    @property
    def default(self) -> list[KitRowDb]:
        return [r for r in self.rows if r.default]


@dataclass
class KitDb:
    code: str
    series: str                       # gruppikit.gruppo
    description: str                  # kit.descr
    collection: str                   # gruppiopzkit.descrizione of kit.raggruppamentoid, "" when none
    found: bool
    note: str = ""                    # why not found (ambiguous name, ...)
    fixed: list[KitRowDb] = field(default_factory=list)
    choices: list[ChoiceGroup] = field(default_factory=list)
    limits: dict[str, float] = field(default_factory=dict)   # non-zero l_vano_min/max, h_vano_min/max, peso_max


@dataclass
class KitsDb:
    kits: dict[str, KitDb] = field(default_factory=dict)     # by FP_KIT code
    notes: list[str] = field(default_factory=list)


# -- helpers --------------------------------------------------------------------------

_KIT_TAG = re.compile(r"<FP_KIT\b[^>]*>")
_ATTR = re.compile(r'\b(Code|Serie)="([^"]*)"')


def _kit_series_from_str(path: Path) -> dict[str, str]:
    """FP_KIT Code -> Serie, read from the STR text (SheetData.kits does not carry the Serie)."""
    try:
        text = Path(path).read_bytes().decode("cp1252", errors="replace")
    except OSError:
        return {}
    out: dict[str, str] = {}
    for tag in _KIT_TAG.findall(text):
        attrs = dict(_ATTR.findall(tag))
        if "Code" in attrs:
            out.setdefault(attrs["Code"], attrs.get("Serie", ""))
    return out


def _s(v) -> str:
    return "" if v is None else str(v).strip()


def _f(v) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _i(v) -> int:
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


def _ids(values) -> str:
    return ",".join(str(int(v)) for v in values)


def _chunks(seq, n=CHUNK):
    seq = list(seq)
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def _quote(code: str) -> str | None:
    """SQL literal for a code, or None when it cannot be quoted safely on every driver (backslash)."""
    return None if "\\" in code else "'" + code.replace("'", "''") + "'"


def _kind(fittizio: int, series: str) -> str:
    if fittizio == 2:
        return "warning"
    if fittizio == 3:
        return "error"
    if fittizio == 1:
        return "machining" if series.casefold() == "easymac" else "fictitious"
    return "hardware"


_TIPO_KIND = {10: "profile", 11: "glass", 12: "panel"}

# range columns: (dim_rif, lim_inf, lim_sup) for ranges 1..8 (FP names them inconsistently)
_RANGE_COLS = [("dim_rif", "lim_inf_range", "lim_sup_range"), ("dimrif2", "liminfrange2", "limsuprange2"),
               ("dim_rif3", "lim_inf_range3", "lim_sup_range3")] + \
              [(f"dimrif{n}", f"liminfrange{n}", f"limsuprange{n}") for n in range(4, 9)]


def _rule(ref: int, lo: float, hi: float) -> SizeRule:
    return SizeRule(ref, DIM_REF_LABELS.get(ref, f"ref {ref}"), lo, hi)


# -- reader ---------------------------------------------------------------------------

def read_kits(db, data: SheetData) -> KitsDb:
    result = KitsDb()
    codes = []
    for g in data.kits:
        for k in g.kits:
            if k.code and k.code not in codes:
                codes.append(k.code)
    if not codes:
        return result
    str_series = _kit_series_from_str(data.path)

    groups = {_i(r[0]): _s(r[1]) for r in db.query("SELECT pkid, gruppo FROM gruppikit")}
    collections = {_i(r[0]): _s(r[1]) for r in db.query("SELECT pkid, descrizione FROM gruppiopzkit")}
    fit_series = {_i(r[0]): _s(r[1]) for r in db.query("SELECT pkid, serie FROM serie_accessori")}
    kit_rows = db.query("SELECT pkid, nomekit, descr, gruppoid, raggruppamentoid, l_vano_min, l_vano_max, "
                        "h_vano_min, h_vano_max, peso_max FROM kit")
    by_name: dict[str, list[tuple]] = {}
    for r in kit_rows:
        by_name.setdefault(_s(r[1]).casefold(), []).append(r)

    chosen: dict[str, tuple] = {}
    for code in codes:
        cands = by_name.get(code.casefold(), [])
        serie = str_series.get(code, "")
        if serie:
            cands = [r for r in cands if groups.get(_i(r[3]), "").casefold() == serie.casefold()]
        if len(cands) == 1:
            chosen[code] = cands[0]
        else:
            note = "kit not found in the database" if not cands else \
                f"{len(cands)} kits share this name and the STR gives no series"
            result.kits[code] = KitDb(code, serie, "", "", False, note)

    if not chosen:
        return result

    # kit rows
    kit_ids = sorted({_i(r[0]) for r in chosen.values()})
    cols = ("kitid, tipo, serieaccessoriid, codice, descr, num_base, opzionale, defflg, gruppoid, dim_calc, "
            "apertura, idriga, " + ", ".join(c for rng in _RANGE_COLS for c in rng))
    rows_by_kit: dict[int, list[tuple]] = {}
    for part in _chunks(kit_ids):
        for r in db.query(f"SELECT {cols} FROM dettagliokit WHERE kitid IN ({_ids(part)})"):
            rows_by_kit.setdefault(_i(r[0]), []).append(r)

    # fittings referenced by the rows: one query per series, codes quoted
    wanted: dict[int, set[str]] = {}
    for rows in rows_by_kit.values():
        for r in rows:
            if _i(r[1]) <= 4 and _s(r[3]):
                wanted.setdefault(_i(r[2]), set()).add(_s(r[3]))
    acc_by_key: dict[tuple[int, str], tuple] = {}     # (serieid, code casefold) -> (pkid, descr, fittizio, sostituisci, code, serieid)
    for serieid, cs in wanted.items():
        quoted = [q for q in (_quote(c) for c in sorted(cs)) if q]
        for part in _chunks(quoted):
            for r in db.query("SELECT pkid, serieid, codice, descr, fittizio, sostituisci FROM accessori "
                              f"WHERE serieid = {int(serieid)} AND codice IN ({', '.join(part)})"):
                acc_by_key[(_i(r[1]), _s(r[2]).casefold())] = (_i(r[0]), _s(r[3]), _i(r[4]), _i(r[5]), _s(r[2]), _i(r[1]))

    resolver = _Replacer(db, fit_series)
    resolver.load(acc_by_key)

    for code, kr in chosen.items():
        kit_id = _i(kr[0])
        limits = {name: _f(v) for name, v in zip(("l_vano_min", "l_vano_max", "h_vano_min", "h_vano_max", "peso_max"),
                                                   kr[5:10]) if _f(v)}
        kd = KitDb(code, groups.get(_i(kr[3]), ""), _s(kr[2]), collections.get(_i(kr[4]), "") if _i(kr[4]) else "",
                   True, limits=limits)
        groups_seen: dict[int, ChoiceGroup] = {}
        for r in sorted(rows_by_kit.get(kit_id, []), key=lambda x: _i(x[11])):
            row = _make_row(r, fit_series, acc_by_key, resolver)
            if row.optional:
                cg = groups_seen.get(row.group_id)
                if cg is None:
                    cg = groups_seen[row.group_id] = ChoiceGroup(row.group_id, collections.get(row.group_id, ""))
                    kd.choices.append(cg)
                cg.rows.append(row)
            else:
                kd.fixed.append(row)
        result.kits[code] = kd
    return result


def _make_row(r, fit_series, acc_by_key, resolver) -> KitRowDb:
    tipo, serieid, code = _i(r[1]), _i(r[2]), _s(r[3])
    series = fit_series.get(serieid, "") if tipo <= 4 else ""
    rules, more = [], False
    for n, (ref_i, lo_i, hi_i) in enumerate(zip(r[12::3], r[13::3], r[14::3])):
        if _i(ref_i):
            if n < 2:
                rules.append(_rule(_i(ref_i), _f(lo_i), _f(hi_i)))
            else:
                more = True
    row = KitRowDb(tipo=tipo, code=code, series=series, description=_s(r[4]), qty=_f(r[5]),
                   kind=_TIPO_KIND.get(tipo, "hardware"), optional=_i(r[6]) == 1, default=_i(r[7]) == 1,
                   group_id=_i(r[8]), dim_calc=_i(r[9]), hand={1: "LH", 2: "RH"}.get(_i(r[10]), ""),
                   rules=rules, more_ranges=more)
    if tipo <= 4:
        acc = acc_by_key.get((serieid, code.casefold()))
        if acc is None:
            row.found, row.kind = False, "unknown"
        else:
            row.kind = _kind(acc[2], series)
            row.replaced_by = resolver.final(acc[0], row.qty)
    return row


class _Replacer:
    """Resolves `sostituisci` + `accessoricollegati` recursively, in Python (no recursive CTE: Access has none)."""

    def __init__(self, db, fit_series):
        self.db = db
        self.fit_series = fit_series
        self.acc: dict[int, tuple] = {}                 # pkid -> (pkid, descr, fittizio, sostituisci, code, serieid)
        self.children: dict[int, list[tuple[int, float]]] = {}

    def load(self, acc_by_key):
        for v in acc_by_key.values():
            self.acc[v[0]] = v
        start_ids = list(self.acc)
        frontier = [i for i in start_ids if self.acc.get(i, (0, 0, 0, 0, '', 0))[3] == 1]
        seen: set[int] = set()
        for _ in range(MAX_DEPTH):
            frontier = [i for i in frontier if i not in seen]
            if not frontier:
                break
            seen.update(frontier)
            nxt: set[int] = set()
            for part in _chunks(frontier):
                for r in self.db.query("SELECT idaccprincipale, idacccollegato, num_base FROM accessoricollegati "
                                       f"WHERE idaccprincipale IN ({_ids(part)})"):
                    self.children.setdefault(_i(r[0]), []).append((_i(r[1]), _f(r[2])))
                    nxt.add(_i(r[1]))
            missing = [i for i in nxt if i not in self.acc]
            for part in _chunks(missing):
                for r in self.db.query("SELECT pkid, serieid, codice, descr, fittizio, sostituisci FROM accessori "
                                       f"WHERE pkid IN ({_ids(part)})"):
                    self.acc[_i(r[0])] = (_i(r[0]), _s(r[3]), _i(r[4]), _i(r[5]), _s(r[2]), _i(r[1]))
            frontier = [i for i in nxt if self.acc.get(i, (0, 0, 0, 0, '', 0))[3] == 1]

    def final(self, pkid: int, qty: float, depth: int = 0, path: tuple = ()) -> list[Resolved]:
        """Hardware that replaces `pkid`; [] when it is not replaced (or the chain is broken)."""
        acc = self.acc.get(pkid)
        kids = self.children.get(pkid)
        if acc is None or acc[3] != 1 or not kids or depth >= MAX_DEPTH or pkid in path:
            return []
        out: list[Resolved] = []
        for cid, cq in kids:
            child = self.acc.get(cid)
            if child is None:
                continue
            sub = self.final(cid, qty * cq, depth + 1, path + (pkid,))
            if sub:
                out.extend(sub)
                continue
            code, serieid = child[4], child[5]
            series = self.fit_series.get(serieid, "")
            out.append(Resolved(code, series, child[1], qty * cq, _kind(child[2], series)))
        return out
