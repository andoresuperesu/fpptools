"""Sheet readers on synthetic fixtures (no client files)."""

import struct

from fpptools import sheet_data
from tests.conftest import make_str

BODY = (
    '  <FP_PREVIEW>\n'
    '    <FP_PATH_VERTEX x="0" y="0"/><FP_PATH_VERTEX x="900" y="0"/>'
    '<FP_PATH_VERTEX x="900" y="2000"/><FP_PATH_VERTEX x="0" y="2000"/>\n'
    '    <FP_VAR VarName="$$EXT$$" VarValue="1"/>\n'
    '  </FP_PREVIEW>\n'
    '  <FP_NODE ElementType="8600" Code="1">\n'
    '    <FP_PIECE Type="8050" DXF="SER_X\\FRAME_A.DXF"/>\n'
    '    <FP_PIECE Type="8050" DXF="SER_X\\FRAME_A.DXF"/>\n'
    '    <FP_PIECE Type="8050" DXF="SER_X\\GHOSTED.DXF" ElementGhost="1"/>\n'
    '    <FP_PIECE Type="8040" DXF=""/>\n'
    '    <FP_KIT Code="K1" Description="KIT ONE" Optional="1" Confirmed="0" Multiply="1">\n'
    '      <FP_FITTING Code="IN-KIT" Type="1" Multiply="1"/>\n'
    '    </FP_KIT>\n'
    '    <FP_NODE ElementType="8610" Code="3">\n'
    '      <FP_PIECE Type="8090" DXF="SER_X\\SASH_B.DXF"/>\n'
    '      <FP_NODE ElementType="8650" Code="11" PaneTableCode="GUID1">\n'
    '        <FP_FITTING Code="SB316" Description="Setting block" Type="1" Multiply="4"/>\n'
    '        <FP_PIECE Type="8510" DXF="GLASSES\\06MM.DXF"/>\n'
    '        <FP_PIECE Type="8180" DXF="SER_X\\BEAD.DXF"/>\n'
    '        <FP_PIECE Type="8180" DXF="SER_X\\BEAD.DXF"/>\n'
    '      </FP_NODE>\n'
    '      <FP_NODE ElementType="8650" Code="12" PaneTableCode="GUID1">\n'
    '        <FP_FITTING Code="SB316" Description="Setting block" Type="1" Multiply="4"/>\n'
    '        <FP_PIECE Type="8510" DXF="GLASSES\\06MM.DXF"/>\n'
    '        <FP_PIECE Type="8180" DXF="SER_X\\BEAD.DXF"/>\n'
    '        <FP_PIECE Type="8180" DXF="SER_X\\BEAD.DXF"/>\n'
    '      </FP_NODE>\n'
    '    </FP_NODE>\n'
    '  </FP_NODE>\n'
)


def _s(text: str, n: int = 41) -> bytes:
    return text.encode("cp1252").ljust(n, b"\0")


def nod_bytes(joints) -> bytes:
    """joints: [(a, b, [(code, descr)])] in the FILE_VERSION=0005 layout."""
    out = b"FILE_VERSION=0005"
    for a, b, fits in joints:
        body = bytearray(339)
        body[0:41] = _s(a)
        struct.pack_into("<H", body, 41, 8050)
        body[43:84] = _s(b)
        struct.pack_into("<H", body, 84, 8090)
        struct.pack_into("<H", body, 337, len(fits))
        out += struct.pack("<HH", 1, 2) + bytes(body)
        for code, descr, qty in fits:
            blk = bytearray(400)
            struct.pack_into("<h", blk, 228, qty)
            blk[60:90] = _s(code, 30)
            blk[90:190] = _s(descr, 100)
            out += bytes(blk)
    return out


def test_read_sheet(tmp_path):
    root = tmp_path / "Str"
    (root / "F").mkdir(parents=True)
    f = root / "F" / "DOOR.STR"
    f.write_bytes(make_str("U1", "A DOOR", BODY))
    nods = tmp_path / "Nod"
    nods.mkdir()
    (nods / "X.NOD").write_bytes(nod_bytes([
        ("SER_X\\FRAME_A.DXF", "SER_X\\SASH_B.DXF", [("CORNER", "Corner key", 2)]),
        ("ser_x\\frame_a.dxf", "SER_X\\SASH_B.DXF", []),
        ("SER_X\\FRAME_A.DXF", "SER_X\\OTHER.DXF", [("NO", "not in style", 1)]),
    ]))
    d = sheet_data.read_sheet(f, root, nods)
    assert (d.folder, d.name, d.unique_code, d.description) == ("F", "DOOR", "U1", "A DOOR")
    assert d.side == "ext" and d.size == (900, 2000) and not d.error
    assert [(p.use, p.series, p.code, p.qty) for p in d.profiles] == [
        ("8050", "SER_X", "FRAME_A", 2), ("8090", "SER_X", "SASH_B", 1), ("8180", "SER_X", "BEAD", 4)]
    assert len(d.kits) == 1 and d.kits[0].node_type == "8600"
    assert d.kits[0].kits[0].code == "K1" and d.kits[0].kits[0].optional and not d.kits[0].kits[0].confirmed
    assert [(g.code, g.openings) for g in d.glazing_fittings] == [("SB316", ["11", "12"])]  # IN-KIT ignored
    assert [(p.glass, p.beads, p.pane_table, p.openings) for p in d.panes] == [
        ("06MM", "BEAD x2", "GUID1", ["11", "12"])]
    assert d.nod_checked and d.joints_without_fittings == 1
    assert [j.fittings for j in d.joints] == [[("CORNER", "Corner key", 2)]]


def test_nod_not_checked_and_bad_files(tmp_path):
    f = tmp_path / "A.STR"
    f.write_bytes(make_str("U", "d", BODY))
    assert sheet_data.read_sheet(f, tmp_path, None).nod_checked is False
    nods = tmp_path / "Nod"
    nods.mkdir()
    (nods / "BAD.NOD").write_bytes(b"garbage")
    d = sheet_data.read_sheet(f, tmp_path, nods)
    assert not d.nod_checked and any("BAD.NOD" in n for n in d.notes)
    broken = tmp_path / "B.STR"
    broken.write_bytes(b"<FP_TREE><oops>")
    assert sheet_data.read_sheet(broken, tmp_path, None).error
