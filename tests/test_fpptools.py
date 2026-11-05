import csv
from pathlib import Path

import pytest
from click.testing import CliRunner
from openpyxl import load_workbook

from fpptools import __version__, config, strfile
from fpptools.cli import cli
from fpptools.commands.fit import fittings_in_design
from fpptools.commands.wipe import wipe_kits, wipe_panedefs
from fpptools.errors import FppToolsError


def run(*args):
    result = CliRunner().invoke(cli, list(map(str, args)), catch_exceptions=False)
    return result


def read_csv(path: Path) -> list[list[str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.reader(f, delimiter=";"))


# -- packaging / CLI ------------------------------------------------------------

def test_version():
    assert run("--version").output.strip().endswith(__version__)


def test_help_without_fp_pro(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))  # no FP_PRO.INI there
    monkeypatch.delenv(config.ENV_INI, raising=False)
    for args in (["--help"], ["str", "list", "--help"], ["fit", "list", "--help"], ["wipe", "panedefs", "--help"]):
        assert run(*args).exit_code == 0, args


def test_missing_ini_is_a_clean_error(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.delenv(config.ENV_INI, raising=False)
    result = CliRunner().invoke(cli, ["str", "list", "-o", "-"])
    assert result.exit_code == 1
    assert "FP Pro configuration not found" in result.output


# -- config ---------------------------------------------------------------------

def test_config_reads_ini(ini, str_root):
    cfg = config.load(ini)
    assert cfg.name == "TEST_CONFIG"
    assert cfg.str_path == str_root
    assert cfg.db_kind == "mysql"
    assert (cfg.mysql.port, cfg.mysql.charset, cfg.mysql.database) == (3307, "latin1", "fp_pro32_test")


def test_mysql_defaults_when_keys_missing(ini):
    text = ini.read_bytes().decode("cp1252")
    text = text.replace("DB_CHARSET=latin1\r\n", "").replace("DB_PORT=3307\r\n", "")
    ini.write_bytes(text.encode("cp1252"))
    s = config.load(ini).mysql
    assert (s.charset, s.port) == ("latin1", 3306)
    ini.write_bytes(text.replace("[MYSQL]\r\n", "[MYSQL]\r\nDB_CHARSET=\r\n").encode("cp1252"))
    assert config.load(ini).mysql.charset == "latin1"  # empty value -> default too


def test_double_click_launcher(ini, tmp_path, monkeypatch):
    from fpptools import quick
    monkeypatch.setenv(config.ENV_INI, str(ini))
    out_dir = tmp_path / "exe_folder"
    out_dir.mkdir()
    assert quick.run(out_dir) == 0
    ws = load_workbook(out_dir / "estructuras.xlsx").active
    assert [c.value for c in ws[1]] == ["Carpeta", "Nombre", "Nombre único", "Descripción"]
    assert ws.max_row == 4


def test_str_list_needs_only_str_path(tmp_path, str_root):
    ini = tmp_path / "MIN.INI"
    ini.write_bytes(f"[SYSTEM]\r\nSTR_PATH={str_root}\r\n".encode("cp1252"))
    assert run("--ini", ini, "str", "list", "-o", tmp_path / "x.csv").exit_code == 0


def test_double_click_launcher_reports_errors(tmp_path, monkeypatch):
    from fpptools import quick
    monkeypatch.setenv(config.ENV_INI, str(tmp_path / "missing.INI"))
    assert quick.run(tmp_path) == 1
    assert not (tmp_path / "estructuras.xlsx").exists()


def test_config_command_hides_password(ini):
    out = run("--ini", ini, "config").output
    assert "TEST_CONFIG" in out and "3307" in out
    assert "secret" not in out


# -- str list -------------------------------------------------------------------

def test_read_info(str_root):
    f = str_root / "019_SERIE_X" / "VENTANA_PROYECTABLE" / "VTA_X_PROY_1CPO.STR"
    info = strfile.read_info(f, str_root)
    assert info.folder == "019_SERIE_X\\VENTANA_PROYECTABLE"
    assert info.name == "VTA_X_PROY_1CPO"
    assert info.unique_code == "SX001"
    assert info.description == "VENTANA PROYECTABLE 1 CUERPO - AÑO ÚNICO"
    assert not info.error


def test_str_list_csv(ini, tmp_path):
    out = tmp_path / "out.csv"
    assert run("--ini", ini, "str", "list", "--lang", "es", "-o", out).exit_code == 0
    assert out.read_bytes().startswith(b"\xef\xbb\xbf")  # BOM for Excel
    rows = read_csv(out)
    assert rows[0] == ["Carpeta", "Nombre", "Nombre único", "Descripción"]
    assert [r[1] for r in rows[1:]] == ["VTA_X_PROY_1CPO", "VTA_X_PROY_2CPO", "PUERTA"]


def test_str_list_under_and_match(ini, tmp_path):
    out = tmp_path / "out.csv"
    run("--ini", ini, "str", "list", "--under", "019_serie_x", "--match", "*2cpo", "-o", out)
    assert [r[2] for r in read_csv(out)[1:]] == ["SX002"]


def test_str_list_xlsx(ini, tmp_path):
    out = tmp_path / "out.xlsx"
    run("--ini", ini, "str", "list", "-o", out)
    ws = load_workbook(out).active
    assert ws["A1"].value == "Folder" and ws.max_row == 4


def test_broken_file_is_reported_not_fatal(ini, str_root, tmp_path):
    (str_root / "OTRA" / "BROKEN.STR").write_bytes(b"<FP_TREE")
    out = tmp_path / "out.csv"
    result = CliRunner().invoke(cli, ["--ini", str(ini), "str", "list", "-o", str(out)])
    assert result.exit_code == 0
    rows = read_csv(out)
    assert rows[0][-1] == "Error"
    assert any(r[1] == "BROKEN" and r[-1] for r in rows[1:])


def test_root_must_exist():
    with pytest.raises(FppToolsError):
        strfile.find_files(Path("/does/not/exist"), (".STR",))


# -- fit list -------------------------------------------------------------------

def test_fittings_with_kits(str_root):
    f = str_root / "019_SERIE_X" / "VENTANA_PROYECTABLE" / "VTA_X_PROY_1CPO.STR"
    rows = fittings_in_design(f, {"KIT-HINGES": ["HINGE-A", "HINGE-B"]})
    codes = [r[0] for r in rows]
    assert codes == ["HANDLE-01", "GLASS-BEAD-CLIP", "HINGE-A", "HINGE-B"]
    assert "IGNORED-INSIDE-KIT" not in codes
    missing = fittings_in_design(f, {})
    assert missing[-1][2] == "kit not found in database"


def test_fit_list_no_db(ini, tmp_path):
    out = tmp_path / "fit.csv"
    assert run("--ini", ini, "fit", "list", "--no-db", "-o", out).exit_code == 0
    rows = read_csv(out)
    assert rows[0] == ["Folder", "File", "Fitting", "Source", "Note"]
    assert ["HANDLE-01", "FP_NODE:1"] == rows[1][2:4]


# -- wipe -----------------------------------------------------------------------

def _pane_file(str_root):
    return str_root / "019_SERIE_X" / "VENTANA_PROYECTABLE" / "VTA_X_PROY_1CPO.STR"


def test_roundtrip_without_changes_is_byte_identical(str_root):
    for f in strfile.find_files(str_root, (".STR",)):
        raw = f.read_bytes()
        assert strfile.serialize(strfile.parse(f)) == raw, f


def test_roundtrip_keeps_mixed_line_endings_in_notes(tmp_path):
    # FP notes (FP_TEXT) can hold LF lines inside a CRLF file
    raw = (b'<?xml version="1.0" encoding="Windows-1252" standalone="no"?>\r\n<FP_TREE NameStr="N">\r\n'
           b"  <FP_TEXT>LINE 1 \nLINE 2\t\t\n\nLINE 4\r\nLAST</FP_TEXT>\r\n  <FP_NOTE />\r\n</FP_TREE>")
    f = tmp_path / "NOTES.STR"
    f.write_bytes(raw)
    assert strfile.serialize(strfile.parse(f)) == raw


def test_wipe_transforms(str_root):
    doc = strfile.parse(_pane_file(str_root))
    actions = wipe_panedefs(doc.tree)
    assert len(actions) == 3
    assert wipe_panedefs(doc.tree) == []  # idempotent
    out = strfile.serialize(doc)
    assert b"GLASS-BEAD-CLIP" not in out and b"VID_6MM" not in out and b"PaneTableCode" not in out
    assert b"HANDLE-01" in out and b"\r\n" in out and b"\n" not in out.replace(b"\r\n", b"")
    assert wipe_kits(doc.tree) == ["kit KIT-HINGES removed"]


def test_wipe_keeps_fp_formatting(str_root):
    f = str_root / "OTRA" / "PUERTA.str"  # LF inside CDATA, CRLF outside, other declaration
    raw = f.read_bytes()
    doc = strfile.parse(f)
    wipe_panedefs(doc.tree)
    out = strfile.serialize(doc)
    assert out.startswith(b'<?xml version="1.0" encoding="windows-1252" standalone="no" ?>\r\n')
    assert b"<FP_TEXT></FP_TEXT>\r\n" in out and b"<FP_PIECE_FLTSX></FP_PIECE_FLTSX>" in out
    assert b'<FP_VAR Code="1" Value=""/>' in out
    assert b"QUJD\nREVG\n]]>" in out and out.endswith(b"</FP_TREE>\r\n")
    # only the wiped lines differ
    removed = set(raw.split(b"\r\n")) - set(out.split(b"\r\n"))
    assert all(b"GLASS-BEAD-CLIP" in l or b"VID_6MM" in l or b"PaneTableCode" in l for l in removed)


def test_wipe_simulate_writes_nothing(ini, str_root, tmp_path):
    before = {p: p.read_bytes() for p in str_root.rglob("*")if p.is_file()}
    result = run("--ini", ini, "wipe", "panedefs", "--backup-dir", tmp_path / "bk")
    assert "SIMULATION" in result.output and "2 file(s) would change, 6 change(s)" in result.output
    assert before == {p: p.read_bytes() for p in str_root.rglob("*") if p.is_file()}
    assert not (tmp_path / "bk").exists()


def test_wipe_apply_backs_up_first(ini, str_root, tmp_path):
    f = _pane_file(str_root)
    original = f.read_bytes()
    result = run("--ini", ini, "wipe", "panedefs", "--apply", "--backup-dir", tmp_path / "bk")
    assert result.exit_code == 0
    backups = list((tmp_path / "bk").iterdir())
    assert len(backups) == 1
    saved = backups[0] / "019_SERIE_X" / "VENTANA_PROYECTABLE" / f.name
    assert saved.read_bytes() == original
    assert (backups[0] / "report.txt").is_file()
    assert b"PaneTableCode" not in f.read_bytes()
    # second run: nothing left to do
    assert "Nothing to change" in run("--ini", ini, "wipe", "panedefs", "--apply",
                                      "--backup-dir", tmp_path / "bk").output


def test_backup_dir_inside_root_is_refused(ini, str_root):
    result = CliRunner().invoke(cli, ["--ini", str(ini), "wipe", "panedefs", "--apply",
                                      "--backup-dir", str(str_root / "bk")])
    assert result.exit_code == 1 and "inside" in result.output


def test_legacy_command_still_works(ini, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(cli, ["--ini", str(ini), "list_fittings", "--searchtype", "str"],
                                catch_exceptions=False, input="")
    # DB is not reachable in tests: the command must fail cleanly, not crash
    assert result.exit_code in (0, 1)
