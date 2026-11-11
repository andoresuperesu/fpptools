"""PDF rendering of one synthetic sheet, with and without database sections (no client files)."""

from pathlib import Path

import pytest

pytest.importorskip("matplotlib")

from fpptools.render import sheet  # noqa: E402
from fpptools.sheet_data import KitGroup, KitRow, PaneRow, ProfileRow, SheetData  # noqa: E402
from fpptools.sheetdb import SheetDb  # noqa: E402
from fpptools.sheetdb.kits import ChoiceGroup, KitDb, KitRowDb, KitsDb, Resolved, SizeRule  # noqa: E402
from fpptools.sheetdb.machinings import MachiningRow, MachiningsDb  # noqa: E402
from fpptools.sheetdb.panes import PaneCombo, PaneFitting, PaneOpening, PanesDb, PaneTable  # noqa: E402
from fpptools.sheetdb.profiles import Component, Fixing, ProfileDb, ProfilesDb  # noqa: E402

STR_XML = (
    '<FP_TREE NameStr="T1"><FP_PREVIEW>'
    '<FP_PATH_VERTEX x="0" y="0"/><FP_PATH_VERTEX x="900" y="0"/>'
    '<FP_PATH_VERTEX x="900" y="2000"/><FP_PATH_VERTEX x="0" y="2000"/>'
    "</FP_PREVIEW></FP_TREE>"
)


def _data() -> SheetData:
    return SheetData(
        path=Path("T1.STR"), folder="SERIE_X", name="T1", unique_code="SX1", description="TEST STYLE", side="int",
        size=(900, 2000),
        profiles=[ProfileRow("8050", "SX", "JAMB", 2), ProfileRow("8180", "SX", "BEAD", 4)],
        kits=[KitGroup("8610", "3", [KitRow("K1", "KIT ONE", True, False, "1")])],
        panes=[PaneRow(["11"], "06MM", "BEAD x4", "ABCDEF0123456789")],
        nod_checked=True, joints_without_fittings=2)


def _db() -> SheetDb:
    fix = Fixing("fitting", "S", "SCREW", "Screw", 2, 38.0, None, False, "", "")
    profiles = ProfilesDb(profiles={
        ("sx", "jamb"): ProfileDb("SX", "JAMB", True, "JAMB TEST", True,
                                  [Component("SX", "MAIN", "Main bar", True, 1)], 44.5, [fix]),
        ("sx", "bead"): ProfileDb("SX", "BEAD", False),
    })
    row = KitRowDb(1, "HW1", "S", "Hinge", 2, "hardware", False, False, 0, 0, "LH",
                   [SizeRule(1, "H", 0, 2286)], False, True,
                   [Resolved("HW2", "S", "Final hinge", 2, "hardware")])
    kits = KitsDb(kits={"K1": KitDb("K1", "S", "KIT ONE", "COLLECTION", True, fixed=[row],
                                    choices=[ChoiceGroup(1, "LOCKS", [row])], limits={"l_vano_min": 500})})
    table = PaneTable("ABCDEF0123456789", "TABLE", 0.5, ["SX"],
                      [PaneCombo(6, 44.5, ["SX\\BEAD"], 0.5, [PaneFitting("1", "SB316", "Block", 4, True)])])
    panes = PanesDb([PaneOpening(["11"], "06MM", "BEAD x4", "ABCDEF0123456789", table)], rooms_resolved=True)
    mach = MachiningsDb([MachiningRow("M1", ["A.LDT"], 1, "Locks", "HW1", "", "Lock", False, ["SX\\JAMB"],
                                      ["SX\\OTHER"], False, [])])
    return SheetDb(profiles, kits, panes, mach)


@pytest.mark.parametrize("with_db,lang", [(True, "en"), (False, "es")])
def test_renders_pdf(tmp_path: Path, with_db: bool, lang: str):
    data = _data()
    if with_db:
        data.db = _db()
    out = tmp_path / "s.pdf"
    pages = sheet.write_pdf([(data, STR_XML)], out, prm_dir=None, sight=None, lang=lang, config_name="CFG",
                            date="2026-01-01", version="0")
    assert pages >= 1
    assert out.read_bytes().startswith(b"%PDF")


def test_db_error_is_not_fatal(tmp_path: Path):
    data = _data()
    data.db = SheetDb(error="connection refused")
    out = tmp_path / "s.pdf"
    assert sheet.write_pdf([(data, STR_XML)], out, prm_dir=None, sight=None) >= 1
