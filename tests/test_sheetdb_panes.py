"""sheetdb.panes against a tiny SQLite stand-in (generic data, no client files)."""

import sqlite3
from pathlib import Path

import pytest

from fpptools.sheet_data import PaneRow, ProfileRow, SheetData
from fpptools.sheetdb.panes import read_panes

GUID = "AAAA1111"


class FakeDB:
    """Same surface as ReadOnlyDB.query, SELECT only."""

    def __init__(self):
        self.c = sqlite3.connect(":memory:")
        c = self.c
        c.executescript("""
            CREATE TABLE serie_profili (pkid INTEGER, serie TEXT);
            CREATE TABLE profili (pkid INTEGER, serieid INTEGER, codice TEXT, spazio_utile REAL);
            CREATE TABLE riempimenti (codice TEXT, descrizione TEXT, tolleranza REAL);
            CREATE TABLE serieprofiloriempimenti (codiceriempimento TEXT, serieprofilo TEXT);
            CREATE TABLE combinazioniriempimenti (codiceriempimento TEXT, spessorevetro REAL, spazioutile REAL,
                codicefermavetro TEXT, codicefermavetro2 TEXT, codicefermavetro3 TEXT, codicefermavetro4 TEXT,
                tolleranza REAL);
            CREATE TABLE accessoririempimenti (codiceriempimento TEXT, spessorevetro REAL, spazioutile REAL,
                tipo INTEGER, codice TEXT, descr TEXT, num_base REAL, predefinito INTEGER);
            INSERT INTO serie_profili VALUES (1, 'SER_A'), (2, 'SER_B');
            INSERT INTO profili VALUES (10, 1, 'SASH', 20.0), (11, 1, 'BEAD', 5.0), (12, 2, 'SASH', 99.0);
            INSERT INTO riempimenti VALUES ('AAAA1111', 'STYLE TABLE', 0.5), ('BBBB2222', 'OTHER TABLE', 0.0),
                ('CCCC3333', 'OTHER SERIES', 0.0);
            INSERT INTO serieprofiloriempimenti VALUES ('AAAA1111', 'SER_A'), ('BBBB2222', 'SER_A'),
                ('CCCC3333', 'SER_B');
            INSERT INTO combinazioniriempimenti VALUES
                ('AAAA1111', 6.0, 20.0, 'SER_A|B1', '', '', '', 0.0),
                ('AAAA1111', 6.0, 30.0, 'SER_A|B9', '', '', '', 0.0),
                ('BBBB2222', 8.0, 20.0, 'SER_A|B2', 'SER_A|B3', '', '', 0.1),
                ('BBBB2222', 8.0, 31.0, 'SER_A|B2', '', '', '', 0.0),
                ('CCCC3333', 8.0, 20.0, 'SER_B|B4', '', '', '', 0.0);
            INSERT INTO accessoririempimenti VALUES
                ('AAAA1111', 6.0, 20.0, 1, 'SB1', 'Setting block', 4, 0),
                ('BBBB2222', 8.0, 20.0, 4, 'SEAL', 'Seal', 2, 1);
        """)

    def query(self, sql, params=()):
        assert sql.lstrip().upper().startswith("SELECT")
        return [tuple(r) for r in self.c.execute(sql, params).fetchall()]


def sheet(pane_table=GUID, profiles=None):
    profiles = profiles if profiles is not None else [
        ProfileRow("8090", "SER_A", "SASH", 2), ProfileRow("8180", "SER_A", "BEAD", 4)]
    return SheetData(Path("x.STR"), "", "x", "", "", "int", profiles=profiles,
                     panes=[PaneRow(["3", "4"], "06MM", "BEAD x4", pane_table)])


def test_style_table_filtered_by_room_with_beads_and_fittings():
    r = read_panes(FakeDB(), sheet())
    assert r.rooms_resolved and r.rooms == {"SER_A\\SASH": 20.0}  # bead room (5) and other series ignored
    t = r.openings[0].table
    assert (t.name, t.tolerance, t.series) == ("STYLE TABLE", 0.5, ["SER_A"])
    assert [(c.thickness, c.room, c.beads) for c in t.combos] == [(6.0, 20.0, ["SER_A\\B1"])]
    assert [(f.code, f.qty, f.default) for f in t.combos[0].fittings] == [("SB1", 4.0, False)]
    assert r.openings[0].openings == ["3", "4"]


def test_could_apply_same_series_and_room_only():
    r = read_panes(FakeDB(), sheet())
    assert [t.name for t in r.could_apply] == ["OTHER TABLE"]      # not the style's own, not SER_B's
    c = r.could_apply[0].combos
    assert len(c) == 1 and c[0].beads == ["SER_A\\B2", "SER_A\\B3"] and c[0].tolerance == 0.1
    assert c[0].fittings[0].default is True


def test_caller_rooms_override_database():
    r = read_panes(FakeDB(), sheet(), room_by_profile={"SER_A\\SASH": 30.0})
    assert [c.beads for c in r.openings[0].table.combos] == [["SER_A\\B9"]]


def test_rooms_not_resolved_leaves_everything_unfiltered_and_flags_it():
    r = read_panes(FakeDB(), sheet(profiles=[ProfileRow("8090", "NOPE", "NOPE", 1)]))
    assert not r.rooms_resolved and "rooms_not_resolved" in r.notes
    assert len(r.openings[0].table.combos) == 2 and r.could_apply == []


def test_missing_or_unknown_pane_table():
    r = read_panes(FakeDB(), sheet(pane_table=""))
    assert r.openings[0].table is None and not any("not found" in n for n in r.notes)
    r = read_panes(FakeDB(), sheet(pane_table="ZZZ"))
    assert r.openings[0].table is None and any("ZZZ" in n for n in r.notes)


def test_quotes_in_values_are_escaped():
    db = FakeDB()
    r = read_panes(db, sheet(pane_table="A'B"))
    assert r.openings[0].table is None


@pytest.mark.parametrize("room", [None, 0])
def test_zero_or_none_rooms_ignored(room):
    r = read_panes(FakeDB(), sheet(), room_by_profile={"SER_A\\SASH": room})
    assert not r.rooms_resolved
