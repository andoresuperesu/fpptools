"""sheetdb.kits against an in-memory SQLite stand-in (generic data, same table/column names as FP Pro)."""

import sqlite3

import pytest

from fpptools import sheet_data
from fpptools.sheetdb.kits import read_kits
from tests.conftest import make_str

RANGE_COLS = ["dim_rif", "lim_inf_range", "lim_sup_range", "dimrif2", "liminfrange2", "limsuprange2",
              "dim_rif3", "lim_inf_range3", "lim_sup_range3"] + \
             [c for n in range(4, 9) for c in (f"dimrif{n}", f"liminfrange{n}", f"limsuprange{n}")]


class FakeDB:
    """Same interface as ReadOnlyDB.query (SELECT only, no parameters), backed by SQLite."""

    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        c = self.conn
        c.execute("CREATE TABLE gruppikit (pkid INTEGER, gruppo TEXT)")
        c.execute("CREATE TABLE gruppiopzkit (pkid INTEGER, descrizione TEXT)")
        c.execute("CREATE TABLE serie_accessori (pkid INTEGER, serie TEXT)")
        c.execute("CREATE TABLE kit (pkid INTEGER, nomekit TEXT, descr TEXT, gruppoid INTEGER, raggruppamentoid INTEGER,"
                  " l_vano_min REAL, l_vano_max REAL, h_vano_min REAL, h_vano_max REAL, peso_max REAL)")
        rng = ", ".join(f"{c_} REAL" for c_ in RANGE_COLS)
        c.execute("CREATE TABLE dettagliokit (kitid INTEGER, tipo INTEGER, serieaccessoriid INTEGER, codice TEXT,"
                  " descr TEXT, num_base REAL, opzionale INTEGER, defflg INTEGER, gruppoid INTEGER, dim_calc INTEGER,"
                  f" apertura INTEGER, idriga INTEGER, {rng})")
        c.execute("CREATE TABLE accessori (pkid INTEGER, serieid INTEGER, codice TEXT, descr TEXT, fittizio INTEGER,"
                  " sostituisci INTEGER)")
        c.execute("CREATE TABLE accessoricollegati (idaccprincipale INTEGER, idacccollegato INTEGER, num_base REAL)")
        self.queries: list[str] = []

    def query(self, sql, params=()):
        assert sql.lstrip().upper().startswith("SELECT")
        assert "WITH" not in sql.upper().split("SELECT")[0] and "RECURSIVE" not in sql.upper()
        self.queries.append(sql)
        return [tuple(r) for r in self.conn.execute(sql).fetchall()]

    def add_row(self, kitid, tipo, serieid, code, descr, qty=1, opt=0, defflg=0, group=0, dim_calc=0, apertura=0,
                idriga=0, ranges=()):
        vals = {c: 0 for c in RANGE_COLS}
        for i, (ref, lo, hi) in enumerate(ranges):
            names = [("dim_rif", "lim_inf_range", "lim_sup_range"), ("dimrif2", "liminfrange2", "limsuprange2"),
                     ("dim_rif3", "lim_inf_range3", "lim_sup_range3")][i]
            vals.update(dict(zip(names, (ref, lo, hi))))
        cols = ["kitid", "tipo", "serieaccessoriid", "codice", "descr", "num_base", "opzionale", "defflg", "gruppoid",
                "dim_calc", "apertura", "idriga"] + RANGE_COLS
        row = [kitid, tipo, serieid, code, descr, qty, opt, defflg, group, dim_calc, apertura, idriga] + \
              [vals[c] for c in RANGE_COLS]
        self.conn.execute(f"INSERT INTO dettagliokit ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", row)


@pytest.fixture
def db():
    d = FakeDB()
    c = d.conn
    c.executemany("INSERT INTO gruppikit VALUES (?,?)", [(1, "SERIES X"), (2, "OTHER")])
    c.executemany("INSERT INTO gruppiopzkit VALUES (?,?)", [(5, "LOCK OPTIONS"), (6, "OPERATIONS")])
    c.executemany("INSERT INTO serie_accessori VALUES (?,?)",
                  [(10, "HW"), (11, "EASYMAC"), (12, "WARNINGS"), (13, "ERRORS"), (14, "HELPER"), (15, "AUX")])
    # kit 100 in SERIES X; kit 101 has the same name in OTHER (ambiguity without a series)
    c.executemany("INSERT INTO kit VALUES (?,?,?,?,?,?,?,?,?,?)", [
        (100, "K_LOCK", "Lock kit", 1, 5, 0, 0, 0, 2400, 0),
        (101, "K_LOCK", "Lock kit (other)", 2, 0, 0, 0, 0, 0, 0),
        (102, "K_HINGE", "Hinge kit", 1, 0, 0, 0, 0, 0, 0),
    ])
    c.executemany("INSERT INTO accessori VALUES (?,?,?,?,?,?)", [
        (1, 10, "PLATE", "Face plate", 0, 0),
        (2, 11, "MACH", "Machining trigger", 1, 0),
        (3, 12, "TOO_WIDE", "Warning text", 2, 0),
        (4, 13, "TOO_SMALL", "Error text", 3, 0),
        (5, 14, "PLACEHOLDER", "placeholder", 1, 0),
        (6, 15, "OPT_A", "Choice A", 0, 1),     # replaced by children 7 (x2) and 8 (-> 9 x3)
        (7, 10, "CYL", "Cylinder", 0, 0),
        (8, 15, "SET", "Set", 0, 1),
        (9, 10, "SCREW", "Screw", 0, 0),
        (10, 15, "OPT_B", "Choice B", 0, 0),
        (11, 10, "HINGE", "Hinge", 0, 0),
        (12, 15, "LOOP1", "Loop 1", 0, 1),      # replacement cycle: 12 -> 13 -> 12
        (13, 15, "LOOP2", "Loop 2", 0, 1),
    ])
    c.executemany("INSERT INTO accessoricollegati VALUES (?,?,?)",
                  [(6, 7, 2), (6, 8, 1), (8, 9, 3), (12, 13, 1), (13, 12, 1)])
    d.add_row(100, 1, 10, "PLATE", "Face plate", idriga=1, apertura=1)
    d.add_row(100, 1, 11, "MACH", "Machining trigger", idriga=2)
    d.add_row(100, 1, 12, "TOO_WIDE", "Warning text", idriga=3, ranges=[(101, 914.5, 9000)])
    d.add_row(100, 1, 13, "TOO_SMALL", "Error text", idriga=4, ranges=[(1, 0, 762), (2, 5, 6)])
    d.add_row(100, 1, 14, "PLACEHOLDER", "placeholder", idriga=5)
    d.add_row(100, 1, 15, "OPT_A", "Choice A", opt=1, defflg=1, group=6, idriga=6)
    d.add_row(100, 1, 15, "OPT_B", "Choice B", opt=1, group=6, idriga=7)
    d.add_row(100, 1, 15, "LOOP1", "Loop", opt=1, group=6, idriga=8)
    d.add_row(100, 1, 10, "NOPE", "not in accessori", idriga=9)
    d.add_row(102, 1, 10, "HINGE", "Hinge", qty=3, idriga=1, dim_calc=1, ranges=[(1, 0, 2286)])
    return d


def make_sheet(tmp_path, kits):
    """A style with the given FP_KIT (code, serie) pairs."""
    body = "  <FP_NODE Code=\"1\" ElementType=\"8610\">\n" + "".join(
        f'    <FP_KIT Brand="" Serie="{s}" Code="{c}" Description="d" Optional="1" Confirmed="0" Multiply="1"/>\n'
        for c, s in kits) + "  </FP_NODE>\n"
    f = tmp_path / "Str" / "S.STR"
    f.parent.mkdir(exist_ok=True)
    f.write_bytes(make_str("U1", "desc", body))
    return sheet_data.read_sheet(f, tmp_path / "Str")


def test_fixed_rows_kinds_and_rules(db, tmp_path):
    res = read_kits(db, make_sheet(tmp_path, [("K_LOCK", "SERIES X"), ("K_HINGE", "SERIES X")]))
    k = res.kits["K_LOCK"]
    assert k.found and k.series == "SERIES X" and k.description == "Lock kit" and k.collection == "LOCK OPTIONS"
    assert k.limits == {"h_vano_max": 2400.0}
    kinds = {r.code: r.kind for r in k.fixed}
    assert kinds == {"PLATE": "hardware", "MACH": "machining", "TOO_WIDE": "warning", "TOO_SMALL": "error",
                     "PLACEHOLDER": "fictitious", "NOPE": "unknown"}
    plate = next(r for r in k.fixed if r.code == "PLATE")
    assert plate.hand == "LH" and plate.series == "HW" and plate.found
    assert next(r for r in k.fixed if r.code == "NOPE").found is False
    wide = next(r for r in k.fixed if r.code == "TOO_WIDE")
    assert [(r.label, r.lo, r.hi) for r in wide.rules] == [("O1", 914.5, 9000)]
    small = next(r for r in k.fixed if r.code == "TOO_SMALL")
    assert [(r.label, r.lo, r.hi) for r in small.rules] == [("H", 0, 762), ("ref 2", 5, 6)]
    hinge = res.kits["K_HINGE"].fixed[0]
    assert hinge.qty == 3 and hinge.dim_calc == 1 and hinge.rules[0].hi == 2286


def test_choices_and_recursive_replacement(db, tmp_path):
    k = read_kits(db, make_sheet(tmp_path, [("K_LOCK", "SERIES X")])).kits["K_LOCK"]
    assert [g.group_id for g in k.choices] == [6]
    g = k.choices[0]
    assert g.name == "OPERATIONS" and len(g.rows) == 3
    assert [r.code for r in g.default] == ["OPT_A"]
    a = g.rows[0]
    # OPT_A -> CYL x2 + SET -> SCREW x3 (recursive)
    assert [(r.code, r.qty, r.kind) for r in a.replaced_by] == [("CYL", 2, "hardware"), ("SCREW", 3, "hardware")]
    assert g.rows[1].replaced_by == []                       # OPT_B is not replaced
    # a replacement cycle (LOOP1 -> LOOP2 -> LOOP1) stops: finite result, the looping fitting listed as itself
    assert [r.code for r in g.rows[2].replaced_by] == ["LOOP1"]


def test_series_disambiguates_and_unknown_kits(db, tmp_path):
    res = read_kits(db, make_sheet(tmp_path, [("K_LOCK", "OTHER"), ("MISSING", "SERIES X")]))
    assert res.kits["K_LOCK"].found and res.kits["K_LOCK"].description == "Lock kit (other)"
    assert res.kits["K_LOCK"].collection == ""
    assert res.kits["MISSING"].found is False and res.kits["MISSING"].note
    # same name, no Serie in the STR: ambiguous -> not resolved, never guessed
    res = read_kits(db, make_sheet(tmp_path, [("K_LOCK", "")]))
    assert res.kits["K_LOCK"].found is False and "share this name" in res.kits["K_LOCK"].note


def test_no_kits_no_queries(db, tmp_path):
    f = tmp_path / "Str" / "E.STR"
    f.parent.mkdir(exist_ok=True)
    f.write_bytes(make_str("U2", "empty"))
    res = read_kits(db, sheet_data.read_sheet(f, tmp_path / "Str"))
    assert res.kits == {} and db.queries == []
