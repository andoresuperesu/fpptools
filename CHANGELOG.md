# Changelog

## 0.3.0 (2026-11-10)

### Added
- `fpptools str sheet`: PDF with one page per structure: elevation (opening symbols, FP-style dimensions) and, beside it, profiles, kits, joinery (NOD multijoints, glazing fittings) and panes read from the STR/NOD files, plus the database sections: profile descriptions and compounds, kit contents (replacement fittings resolved, choices, size ranges), profile fixings, pane tables and machinings (read-only; `--no-db` skips them). Optional extra: `pip install fpptools[report]` (matplotlib). Titles use the bundled Barlow font (SIL OFL).

## 0.2.1 (unreleased)

### Added
- Documentation in `docs/` (one page per command, common options, exes, development). The README is now a short overview that links to it (absolute GitHub links, so they work on PyPI too); `docs/` is in the sdist.

### Changed
- `wipe kits --help` explains `--source`.
- `scripts\build_exe.ps1` builds the exes into `dist_exe\`, leaving `dist\` for the PyPI wheel/sdist.
- Project URL: github.com/andoresuperesu/fpptools.
- Author email: me@aperezc.xyz.

## 0.2.0 (2026-11-05)

Rewrite for current Python and FP Pro 11.

### Added
- `fpptools str list`: structures with folder, name, unique code (NameStr) and description (decoded from Base64). CSV (`;`, UTF-8 BOM) or `.xlsx`, `--lang es`.
- `fpptools_estructuras.exe` / `fpptools-estructuras`: double-click export of structures to `estructuras.xlsx` next to the exe.
- `fpptools config`: show the active configuration (password hidden).
- `fpptools wipe panedefs` and `fpptools wipe kits`: simulate by default; `--apply` backs up every file first and writes a report.
- `--under`, `--match`, `--root` on every folder-scanning command; `--ini` / `FPPTOOLS_INI` on all commands.
- Tests with generic fixtures.

### Changed
- `list_fittings` is now `fpptools fit list` (old syntax kept as a hidden, deprecated alias). Output is CSV with `;`; columns Folder, File, Fitting, Source, Note.
- Job selection uses `--job NAME` (prompted if missing).
- Rewritten files keep FP Pro's format: original XML declaration, windows-1252, CRLF.
- Packaging: uv + hatchling, Python >= 3.10, click 8, lxml 5+, PyMySQL 1.x, pyodbc 5 (Windows only).

### Fixed
- Importing fpptools no longer reads FP_PRO.INI or connects to the database (`--help` works without FP Pro).
- MySQL now uses `DB_PORT` and `DB_CHARSET` from FP_PRO.INI (defaults 3306 and latin1 when missing or empty).
- Access kits query no longer exhausts its cursor after the first file.
- Clean error messages instead of tracebacks when the INI, folders or database are missing.

## 0.1.1

- `list_fittings` for str/blk/job/jobs.
