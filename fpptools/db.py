"""Read-only access to the FP Pro database of the active configuration (MySQL or Access).

Only SELECT statements are allowed. Connections open lazily, on first query.
"""

from __future__ import annotations

import re
from collections import defaultdict

from fpptools.config import FppConfig
from fpptools.errors import FppToolsError

_SELECT = re.compile(r"^\s*(SELECT|WITH)\b", re.IGNORECASE)
ACCESS_DRIVER = "{Microsoft Access Driver (*.mdb, *.accdb)}"


class ReadOnlyDB:
    def __init__(self, cfg: FppConfig):
        self.cfg = cfg
        self._conn = None

    def _connect(self):
        if self._conn is not None:
            return self._conn
        if self.cfg.db_kind == "mysql":
            try:
                import pymysql
            except ImportError as exc:
                raise FppToolsError("MySQL configurations need the 'pymysql' package.") from exc

            s = self.cfg.mysql
            try:
                self._conn = pymysql.connect(
                    host=s.host, port=s.port, user=s.user, password=s.password,
                    database=s.database, charset=s.charset,
                    cursorclass=pymysql.cursors.Cursor, autocommit=True,
                )
            except pymysql.MySQLError as exc:
                raise FppToolsError(f"MySQL connection to {s.host}:{s.port}/{s.database} failed: {exc}") from exc
        else:
            try:
                import pyodbc
            except ImportError as exc:  # non-Windows, or pyodbc not installed
                raise FppToolsError("Access configurations need pyodbc (Windows) and the Microsoft Access ODBC driver.") from exc
            mdb = self.cfg.mdb_file
            if not mdb.is_file():
                raise FppToolsError(f"Access database not found: {mdb}")
            try:
                self._conn = pyodbc.connect(f"DRIVER={ACCESS_DRIVER};DBQ={mdb};ReadOnly=1;", readonly=True)
            except pyodbc.Error as exc:
                raise FppToolsError(
                    f"Access connection to {mdb} failed: {exc}\n"
                    "The Access ODBC driver must match Python's bitness (32/64-bit)."
                ) from exc
        return self._conn

    def query(self, sql: str, params: tuple = ()) -> list[tuple]:
        if not _SELECT.match(sql):
            raise FppToolsError("fpptools only runs read-only (SELECT) queries.")
        cur = self._connect().cursor()
        try:
            cur.execute(sql, params) if params else cur.execute(sql)
            return [tuple(r) for r in cur.fetchall()]
        finally:
            cur.close()

    def close(self):
        if self._conn is not None:
            self._conn.close()
            self._conn = None


KIT_FITTINGS_SQL = (
    "SELECT kit.nomekit, dettagliokit.codice "
    "FROM dettagliokit INNER JOIN kit ON kit.pkid = dettagliokit.kitid"
)


def kit_fittings(db: ReadOnlyDB) -> dict[str, list[str]]:
    """Kit name -> fitting codes it contains."""
    kits: dict[str, list[str]] = defaultdict(list)
    for name, code in db.query(KIT_FITTINGS_SQL):
        kits[str(name)].append(str(code))
    return dict(kits)
