"""sheetdb.profiles on a SQLite stand-in (same tables/columns as FP's archive, generic data)."""

import sqlite3
from pathlib import Path

import pytest

from fpptools.sheet_data import ProfileRow, SheetData
from fpptools.sheetdb.profiles import read_profiles


class FakeDB:
    """Same .query(sql) interface as db.ReadOnlyDB, backed by SQLite."""

    def __init__(self):
        self.c = sqlite3.connect(":memory:")
        self.sql: list[str] = []
        self.c.executescript("""
        CREATE TABLE serie_profili (pkid INTEGER, serie TEXT);
        CREATE TABLE profili (pkid INTEGER, serieid INTEGER, codice TEXT, descr TEXT, composto INTEGER,
                              spazio_utile REAL);
        CREATE TABLE profilicomponenti (pkid INTEGER, profcompostoid INTEGER, profcomponenteid INTEGER,
                                        master INTEGER);
        CREATE TABLE fissaggi (pkid INTEGER, idprof INTEGER, idacc INTEGER, tipo INTEGER, lung REAL,
                               num_base INTEGER, num_max INTEGER, opzionale INTEGER, utilizzo TEXT);
        CREATE TABLE serie_accessori (pkid INTEGER, serie TEXT);
        CREATE TABLE accessori (pkid INTEGER, serieid INTEGER, codice TEXT, descr TEXT);
        INSERT INTO serie_profili VALUES (1, 'SER_A'), (2, 'SER B');
        INSERT INTO profili VALUES
          (10, 1, 'FRAME', 'Frame 50', 0, 24.0),
          (11, 1, 'BEAD', 'Bead', 0, 0.0),
          (12, 1, 'BEAD+BEAD', '', 1, 0.0),
          (13, 2, 'MAIN', 'Main bar', 0, NULL),
          (14, 2, 'COMP', 'Compound', 1, 0.0),
          (15, 2, 'NOMASTER', 'Compound without master', 1, 0.0),
          (16, 2, 'OTHER', 'Other', 0, 0.0);
        INSERT INTO profilicomponenti VALUES
          (1, 12, 11, 0), (2, 12, 11, 0),
          (3, 14, 13, 1), (4, 14, 16, 0),
          (5, 15, 11, 0), (6, 15, 16, 0);
        INSERT INTO serie_accessori VALUES (5, 'ACC_S');
        INSERT INTO accessori VALUES (100, 5, 'SCREW', 'Screw 1/4''');
        INSERT INTO fissaggi VALUES
          (1, 10, 100, 1, 0.0, 4, 0, 0, NULL),
          (2, 10, 16, 10, 38.0, 2, 0, 1, 'x'),
          (3, 10, 999, 10, 10.0, 1, 0, 0, NULL),
          (4, 13, 100, 1, 0.0, 6, 3, 0, NULL),
          (5, 14, 100, 1, 0.0, 9, 0, 0, NULL),
          (6, 10, 100, 7, 0.0, 1, 0, 0, NULL);
        """)

    def query(self, sql, params=()):
        assert sql.lstrip().upper().startswith("SELECT")
        assert "fp_utenti" not in sql.lower() and "passwd" not in sql.lower()
        self.sql.append(sql)
        return [tuple(r) for r in self.c.execute(sql).fetchall()]


def sheet(*profiles) -> SheetData:
    s = SheetData(Path("x.STR"), "", "x", "", "", "int")
    s.profiles = [ProfileRow("8050", ser, code, 1) for ser, code in profiles]
    return s


@pytest.fixture
def db():
    return FakeDB()


def test_description_room_and_unknown(db):
    res = read_profiles(db, sheet(("SER_A", "FRAME"), ("SER_A", "NOPE"), ("NOSER", "X")))
    f = res.get("ser_a", "frame")
    assert f.found and f.description == "Frame 50" and f.glazing_room == 24.0 and not f.compound
    assert not res.get("SER_A", "NOPE").found and not res.get("NOSER", "X").found


def test_fixings_fitting_profile_and_unresolved(db):
    f = read_profiles(db, sheet(("SER_A", "FRAME"))).get("SER_A", "FRAME")
    fit, prof, orphan, unknown = f.fixings
    assert (fit.kind, fit.series, fit.code, fit.description, fit.qty, fit.cut_length) == \
        ("fitting", "ACC_S", "SCREW", "Screw 1/4'", 4, 0.0)
    assert (prof.kind, prof.series, prof.code, prof.cut_length, prof.optional, prof.use) == \
        ("profile", "SER B", "OTHER", 38.0, True, "x")
    assert orphan.kind == "profile" and orphan.code == "" and orphan.description == ""   # not resolved
    assert unknown.kind == "unknown" and unknown.code == ""


def test_series_with_space_spelling(db):
    p = read_profiles(db, sheet(("SER_B", "MAIN"))).get("SER_B", "MAIN")
    assert p.found and p.description == "Main bar" and p.glazing_room is None
    assert p.fixings[0].max_qty == 3


def test_compound_components_dedup_and_main_fixings(db):
    res = read_profiles(db, sheet(("SER_B", "COMP"), ("SER_A", "BEAD+BEAD")))
    comp = res.get("SER_B", "COMP")
    assert comp.compound
    assert [(c.code, c.master) for c in comp.components] == [("MAIN", True), ("OTHER", False)]
    # fixings come from the main profile (MAIN), not from rows on the compound itself
    assert [(x.qty, x.from_profile) for x in comp.fixings] == [(6, "MAIN")]
    twin = res.get("SER_A", "BEAD+BEAD")
    assert [(c.code, c.count) for c in twin.components] == [("BEAD", 2)]
    assert twin.fixings == [] and "main profile" in twin.fixings_note


def test_compound_without_master_is_not_guessed(db):
    p = read_profiles(db, sheet(("SER_B", "NOMASTER"))).get("SER_B", "NOMASTER")
    assert p.compound and p.fixings == [] and p.fixings_note == "compound without a main profile"


def test_quotes_are_escaped_and_select_only(db):
    read_profiles(db, sheet(("SER'A", "CO'DE")))
    assert any("'SER''A'" in q for q in db.sql)
    assert all(q.lstrip().upper().startswith("SELECT") for q in db.sql)


def test_empty_style_runs_no_query(db):
    assert read_profiles(db, sheet()).profiles == {}
    assert db.sql == []
