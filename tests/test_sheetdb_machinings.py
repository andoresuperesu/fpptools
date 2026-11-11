"""Machinings reader: SQLite stand-in for the two FP tables (same column names, generic data)."""

import sqlite3
from pathlib import Path

import pytest

from fpptools.sheet_data import ProfileRow, SheetData
from fpptools.sheetdb.machinings import read_machinings


class FakeDB:
    def __init__(self):
        self.con = sqlite3.connect(":memory:")
        self.con.execute(
            "CREATE TABLE ldtaccessori (serieprofilo1, codiceprofilo1, serieprofilo2, codiceprofilo2, "
            "serieprofilo3, codiceprofilo3, serieprofilo4, codiceprofilo4, ldt, ldt2, ldt3, ldt4, macchina, "
            "marca, serie, codice, tipolav, descrizione, disabled)")
        self.con.execute("CREATE TABLE profcompatldt (macchina, ldt, serie, codice, seriebase, codicebase)")

    def add(self, p1, p2=("", ""), ldt="A.LDT", ldt2="", machine="M1", fitting="FIT1", tipolav=6, disabled=0):
        self.con.execute("INSERT INTO ldtaccessori VALUES (?,?,?,?,'','','','',?,?,'','',?,'BR','SER',?,?,'',?)",
                         (*p1, *p2, ldt, ldt2, machine, fitting, tipolav, disabled))

    def query(self, sql, params=()):
        assert sql.lstrip().upper().startswith("SELECT")
        return [tuple(r) for r in self.con.execute(sql, params).fetchall()]


def data(*profiles):
    return SheetData(Path("x.STR"), "", "x", "", "", "int",
                     profiles=[ProfileRow("8050", s, c, 1) for s, c in profiles])


@pytest.fixture
def db():
    d = FakeDB()
    d.add(("SERX", "SASH1"), ("SERX", "FRAME9"), ldt="HINGE.LDT", ldt2="EMPTY", fitting="HNG", tipolav=6)
    d.add(("serx", "frame2"), ldt="LOCK.LDT", ldt2="STK.LDT", machine="M2", fitting="LCK", tipolav=7, disabled=1)
    d.add(("OTHER", "P"), ldt="NOPE.LDT")
    d.con.execute("INSERT INTO profcompatldt VALUES ('M1','BASE.LDT','SERX','SASH1','SERX','SASH0')")
    d.con.execute("INSERT INTO profcompatldt VALUES ('M1','BASE.LDT','OTHER','Q','OTHER','P')")
    return d


def test_matches_case_insensitive_and_reports_partner(db):
    r = read_machinings(db, data(("SERX", "SASH1"), ("SERX", "FRAME2")))
    assert [m.ldts for m in r.machinings] == [["HINGE.LDT"], ["LOCK.LDT", "STK.LDT"]]  # EMPTY dropped
    hinge, lock = r.machinings
    assert hinge.kind == "Hinges" and hinge.profiles_in_style == ["SERX\\SASH1"]
    assert hinge.profiles_not_in_style == ["SERX\\FRAME9"]          # partner of another series/code
    assert lock.disabled and lock.machine == "M2" and lock.profiles_in_style == ["serx\\frame2"]
    assert r.resolved


def test_unrelated_rows_and_compat(db):
    r = read_machinings(db, data(("SERX", "SASH1")))
    assert len(r.machinings) == 1
    assert [(c.profile, c.base_profile) for c in r.compat] == [("SERX\\SASH1", "SERX\\SASH0")]


def test_fitting_carried_by_style_kits(db):
    d = data(("SERX", "SASH1"), ("SERX", "FRAME2"))
    assert [m.in_style_kits for m in read_machinings(db, d).machinings] == [None, None]   # unknown
    r = read_machinings(db, d, {"KIT-A": {"hng"}, "KIT-B": {"OTHERFIT"}})
    hinge, lock = r.machinings
    assert hinge.in_style_kits is True and hinge.kits == ["KIT-A"]
    assert lock.in_style_kits is False and lock.kits == []
    assert read_machinings(db, d, {"HNG"}).machinings[0].in_style_kits is True      # plain set


def test_no_profiles_and_query_failure():
    assert read_machinings(FakeDB(), data()).machinings == []

    class Broken:
        def query(self, sql, params=()):
            raise RuntimeError("boom")

    r = read_machinings(Broken(), data(("S", "C")))
    assert not r.resolved and "boom" in r.note and r.machinings == []
