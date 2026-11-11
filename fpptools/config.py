"""Read the FP Pro configuration that is currently active (FP_PRO.INI).

FP Pro keeps one active configuration at a time; its folders and database live in
%APPDATA%\\Emmegisoft\\FP_PRO\\FP_PRO.INI. Keys used here (verified on FP Pro 11):

    [SYSTEM] STR_PATH, BLK_PATH, JOB_PATH, MDB_PATH, CONFIGS_PATH, CONN_STR_FP_PRO
    [GENERAL] CURRENT_CONFIGURATION
    [MYSQL]  DB_SERVER_NAME, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DB_CHARSET

CONN_STR_FP_PRO = 1 -> MySQL, 0 -> Access (Fp_Pro32.MDB inside MDB_PATH).
Nothing is read until a command needs it, so `fpptools --help` works without FP Pro.
"""

from __future__ import annotations

import configparser
import os
from dataclasses import dataclass
from pathlib import Path

from fpptools.errors import FppToolsError

INI_ENCODING = "cp1252"
ENV_INI = "FPPTOOLS_INI"


def default_ini_path() -> Path:
    appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(appdata) / "Emmegisoft" / "FP_PRO" / "FP_PRO.INI"


@dataclass(frozen=True)
class MySqlSettings:
    host: str
    port: int
    database: str
    user: str
    password: str
    charset: str


class FppConfig:
    def __init__(self, ini_path: Path, parser: configparser.ConfigParser):
        self.ini_path = ini_path
        self._p = parser

    # -- raw access -------------------------------------------------------
    def get(self, section: str, key: str, default: str | None = None) -> str | None:
        try:
            value = self._p.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return default
        return value.strip().strip('"') if value is not None else default

    def require(self, section: str, key: str) -> str:
        value = self.get(section, key)
        if not value:
            raise FppToolsError(f"[{section}] {key} is missing or empty in {self.ini_path}")
        return value

    def path(self, key: str) -> Path:
        value = self.require("SYSTEM", key)
        if len(value) > 3:  # FP writes folders with a trailing backslash; keep "C:\" intact
            value = value.rstrip("\\/")
        return Path(value)

    # -- convenience --------------------------------------------------------
    @property
    def name(self) -> str:
        return self.get("GENERAL", "CURRENT_CONFIGURATION", "") or ""

    @property
    def str_path(self) -> Path:
        return self.path("STR_PATH")

    @property
    def blk_path(self) -> Path:
        return self.path("BLK_PATH")

    @property
    def job_path(self) -> Path:
        return self.path("JOB_PATH")

    @property
    def nodes_path(self) -> Path | None:
        """Multijoint (.NOD) folder of the configuration, if the INI has it."""
        return self.path("NODES_PATH") if self.get("SYSTEM", "NODES_PATH") else None

    @property
    def prm_path(self) -> Path | None:
        """Opening-symbol scripts (.PRM): <START_PATH>\\Prm (shared by all configurations)."""
        start = self.get("SYSTEM", "START_PATH")
        return Path(start.rstrip("\\/")) / "Prm" if start else None

    @property
    def configs_path(self) -> Path | None:
        return self.path("CONFIGS_PATH") if self.get("SYSTEM", "CONFIGS_PATH") else None

    @property
    def db_kind(self) -> str:
        """'mysql' or 'access'."""
        return "mysql" if self.get("SYSTEM", "CONN_STR_FP_PRO", "0") == "1" else "access"

    @property
    def mdb_file(self) -> Path:
        return self.path("MDB_PATH") / "Fp_Pro32.MDB"

    @property
    def mysql(self) -> MySqlSettings:
        port = self.get("MYSQL", "DB_PORT") or "3306"
        try:
            port_n = int(port)
        except ValueError as exc:
            raise FppToolsError(f"[MYSQL] DB_PORT is not a number: {port!r}") from exc
        return MySqlSettings(
            host=self.get("MYSQL", "DB_SERVER_NAME") or "localhost",
            port=port_n,
            database=self.require("MYSQL", "DB_NAME"),
            user=self.require("MYSQL", "DB_USER"),
            password=self.get("MYSQL", "DB_PASSWORD") or "",
            charset=self.get("MYSQL", "DB_CHARSET") or "latin1",
        )

    def root_for(self, kind: str) -> Path:
        """Folder for 'str', 'blk' or 'job'."""
        return self.path({"str": "STR_PATH", "blk": "BLK_PATH", "job": "JOB_PATH"}[kind])


def _parser() -> configparser.ConfigParser:
    p = configparser.ConfigParser(interpolation=None, strict=False, comment_prefixes=(";", "#"))
    p.optionxform = str.upper  # FP writes keys upper-case; be tolerant of mixed case
    return p


def load(ini: Path | None = None) -> FppConfig:
    """Load the given INI, $FPPTOOLS_INI, or the one FP Pro is using."""
    ini_path = Path(ini or os.environ.get(ENV_INI) or default_ini_path())
    if not ini_path.is_file():
        raise FppToolsError(
            f"FP Pro configuration not found: {ini_path}\n"
            "Open FP Pro once with the wanted configuration, or pass --ini."
        )
    text = ini_path.read_bytes().decode(INI_ENCODING, errors="replace")
    if not text.lstrip().startswith("["):
        text = "[__TOP__]\n" + text
    p = _parser()
    try:
        p.read_string(text, source=str(ini_path))
    except configparser.Error as exc:
        raise FppToolsError(f"Cannot parse {ini_path}: {exc}") from exc
    # Section names are case-sensitive in configparser; FP uses upper case. Normalise.
    norm = _parser()
    for section in p.sections():
        name = section.upper()
        if not norm.has_section(name):
            norm.add_section(name)
        for key, value in p.items(section, raw=True):
            norm.set(name, key, value)
    return FppConfig(ini_path, norm)
