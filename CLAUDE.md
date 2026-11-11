# fpptools: notes for Claude

Andrés's FP Pro admin/debug CLI, published on PyPI as `fpptools`. Users: FP Pro technicians and knowledgeable clients. CLI first; a GUI may come later, so keep logic out of the click commands where practical.

## Rules
- Git: Claude runs git only on Andrés's explicit go-ahead for that action ("commit", "push"...); each go-ahead covers that action only. Otherwise edit files and tell him what is ready to commit. Stage by path (never `git add -A`; `out/` is scratch), never push or rewrite history without being asked.
- Agree changes with Andrés before modifying the repo.
- PyPI package: keep the name `fpptools`, the `fpptools` console script and backwards-compatible commands (hidden aliases when renaming). Bump `fpptools/__init__.py` `__version__` and `CHANGELOG.md`.
- Commands that modify FP files: simulate by default, `--apply` writes, always back up first (`safe_write.py`). Backups must never land inside the scanned folder.
- FP files are windows-1252 XML with CRLF; write through `strfile.serialize` (keeps the original declaration and line endings). Unchanged files must round-trip byte-identical.
- Database access is SELECT-only (`db.ReadOnlyDB`). MySQL and Access both supported. Never read `fp_utenti.passwd`.
- Tests use generic fixtures only (`tests/conftest.py`), never client files.

## Layout
- `fpptools/config.py`: active FP_PRO.INI (lazy). Keys verified on FP Pro 11: [SYSTEM] STR/BLK/JOB/MDB/CONFIGS_PATH, CONN_STR_FP_PRO; [GENERAL] CURRENT_CONFIGURATION; [MYSQL] DB_SERVER_NAME, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DB_CHARSET.
- `fpptools/db.py`: read-only MySQL/Access, kit query.
- `fpptools/strfile.py`: find/read/parse/serialize STR/BLK; `read_info` for name/NameStr/description.
- `fpptools/safe_write.py`: ChangeSet, backup-then-write.
- `fpptools/output.py`: CSV (`;`, utf-8-sig) / xlsx.
- `fpptools/quick.py`: double-click launcher (`fpptools_estructuras.exe`): str list -> estructuras.xlsx next to the exe, pauses before closing.
- `scripts/exe_*.py`: PyInstaller entry scripts. Keep them outside the package: an entry script inside `fpptools/` would put that folder on sys.path and `fpptools/fpptools.py` (0.1 compatibility shim) would shadow the package.
- `fpptools/commands/`: `config_cmd`, `str` (str list), `fit` (fit list + legacy list_fittings), `wipe`.

## Run
```powershell
uv sync; uv run pytest; uv run fpptools --help
.\scripts\build_exe.ps1
```

## Unverified / open
- Job record file naming (`<JOB>_JOBRECORD*.XML`, job/item split) is carried over from 0.1; not checked on FP Pro 11.
- Description decoding assumes cp1252 for non-ASCII text (no accented sample seen yet).
- Future: read several configurations from CONFIGS_PATH (`C:\FP_PRO\CONFIGS`).
