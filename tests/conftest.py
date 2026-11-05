"""Generic FP Pro fixtures (no client data). Shapes copied from real FP Pro 11 files."""

import base64
from pathlib import Path

import pytest

DECL = b'<?xml version="1.0" encoding="Windows-1252" standalone="no"?>'


def b64(text: str) -> str:
    return base64.b64encode(text.encode("cp1252")).decode("ascii")


def make_str(name_str: str, description: str, body: str = "", decl: bytes = DECL,
             cdata_lf: bool = False) -> bytes:
    """Like FP: CRLF everywhere; some files keep LF inside CDATA (cdata_lf).
    Empty elements appear both as <X></X> and <X/>."""
    cdata_nl = "\x00" if cdata_lf else "\n"
    xml = (
        f'<FP_TREE Description="SEE CDATA BELOW..." Fp_Pro_Ver="11" LastNodeCode="9" NameStr="{name_str}" '
        f'PiecesNumber="4" VarNumber="1" Version="1" VertexNumber="4">\n'
        f"  <FP_TEXT></FP_TEXT>\n"
        f'  <FP_DESCRIPTION DescrB64="DESCRIPTION IS B64 CODED"><![CDATA[{b64(description)}{cdata_nl}]]></FP_DESCRIPTION>\n'
        f"{body}"
        f'  <FP_PIECE_FLTSX></FP_PIECE_FLTSX>\n'
        f'  <FP_VAR Code="1" Value=""/>\n'
        f"  <picture><![CDATA[QUJD{cdata_nl}REVG{cdata_nl}]]></picture>\n"
        f"</FP_TREE>"
    )
    data = (decl + b"\n" + xml.encode("cp1252")).replace(b"\n", b"\r\n")
    return data.replace(b"\x00", b"\n")


PANE_BODY = (
    '  <FP_NODE Code="1" ElementType="8600">\n'
    '    <FP_FITTING Code="HANDLE-01" Qty="1"/>\n'
    '    <FP_NODE Code="2" ElementType="8650" PaneTableCode="PT-6MM">\n'
    '      <FP_FITTING Code="GLASS-BEAD-CLIP" Qty="4"/>\n'
    '      <FP_PIECE Code="3" DXF="VID_6MM" Type="8510"/>\n'
    '    </FP_NODE>\n'
    '    <FP_KIT Code="KIT-HINGES">\n'
    '      <FP_FITTING Code="IGNORED-INSIDE-KIT"/>\n'
    '    </FP_KIT>\n'
    '  </FP_NODE>\n'
)


@pytest.fixture
def str_root(tmp_path: Path) -> Path:
    root = tmp_path / "Str"
    (root / "019_SERIE_X" / "VENTANA_PROYECTABLE").mkdir(parents=True)
    (root / "OTRA").mkdir()
    (root / "019_SERIE_X" / "VENTANA_PROYECTABLE" / "VTA_X_PROY_1CPO.STR").write_bytes(
        make_str("SX001", "VENTANA PROYECTABLE 1 CUERPO - AÑO ÚNICO", PANE_BODY))
    (root / "019_SERIE_X" / "VENTANA_PROYECTABLE" / "VTA_X_PROY_2CPO.STR").write_bytes(
        make_str("SX002", "VENTANA PROYECTABLE 2 CUERPOS").replace(b"/>", b" />"))  # newer FP style
    (root / "OTRA" / "PUERTA.str").write_bytes(
        make_str("PU01", "PUERTA", PANE_BODY, decl=b'<?xml version="1.0" encoding="windows-1252" standalone="no" ?>',
                 cdata_lf=True) + b"\r\n")
    (root / "OTRA" / "notes.txt").write_text("not a structure")
    return root


@pytest.fixture
def ini(tmp_path: Path, str_root: Path) -> Path:
    path = tmp_path / "FP_PRO.INI"
    text = (
        "[SYSTEM]\r\n"
        f"STR_PATH={str_root}\\\r\n"
        f"BLK_PATH={tmp_path / 'Blk'}\\\r\n"
        f"JOB_PATH={tmp_path / 'Job'}\\\r\n"
        f"MDB_PATH={tmp_path / 'Mdb'}\\\r\n"
        "CONN_STR_FP_PRO=1\r\n"
        "[GENERAL]\r\nCURRENT_CONFIGURATION=TEST_CONFIG\r\nSEP_STR_UNIQUENAME=\" \"\r\n"
        "[MYSQL]\r\nDB_SERVER_NAME=localhost\r\nDB_NAME=fp_pro32_test\r\nDB_PORT=3307\r\n"
        "DB_USER=reader\r\nDB_PASSWORD=secret\r\nDB_CHARSET=latin1\r\n"
    )
    path.write_bytes(text.encode("cp1252"))
    return path
