# Request: `fpptools str sheet` (style sheets)

Status: phase 1 implemented (2026-11-10), phase 2 (database) implemented (2026-11-10). Open: checked only on the DESA door library (MySQL); Access not tried; hinge machinings come as "Others"; NOD quantity sign (negative values) not interpreted.

## Goal

One PDF page per structure (.STR): the item elevation on the left, and on the right everything the library applies to it, so a technician can review a style without opening FP Pro or the database:

1. Profiles applied
2. Kits applied, with their hardware
3. Multijoint fittings and profile fixings (joinery)
4. Pane tables that could apply
5. Machinings that could apply

It works on the active FP Pro configuration (FP_PRO.INI), like the other commands. It is read-only: it never writes STR, NOD, PRM or database data.

## Command

```
fpptools str sheet [--root DIR] [--under FOLDER] [--match PATTERN] [-o sheets.pdf]
                   [--page letter] [--sight int|ext] [--lang en|es]
```

- Same file selection as `str list` (`--root`, `--under`, `--match`).
- Output: one multi-page PDF (default `str_sheets.pdf`); one sheet per style, plus continuation pages when the lists don't fit.
- `--page letter` (landscape) is the default; keep it open for `tabloid` later.
- `--sight`: draw the elevation as seen from inside or outside (mirrors when the style side differs, as FP does).

## Sheet layout (Letter landscape)

- Header: style name, folder, unique code (NameStr), description, configuration name, date.
- Left (about 55%): elevation drawn from the STR (FP_PREVIEW polygons, layers, ghost pieces dotted, clearance lines, PRM opening symbols, FP-style dimensions), profile labels on each piece.
- Right (about 45%): the five sections below, compact tables.

## Sections and data sources

### 1. Profiles
Every FP_PIECE (not glass) of the style: use (piece Type → readable name: frame, sash, mullion, transom, glazing bead...), series and code (from the DXF path), description, compound yes/no and its components.
- STR: FP_PIECE Type / DXF.
- DB: `profili` (+ `serie_profili`), `profilicomponenti` for compounds.

### 2. Kits
Every FP_KIT on every node, grouped by node (frame, sash...):
- kit code and description, optional or always applied, collection it belongs to;
- fixed rows: final hardware codes and quantities, after resolving replacement fittings (`accessori.sostituisci` + `accessoricollegati`, recursively);
- choices summarised, not expanded: e.g. "16 operations, default: 1in cylinder × thumbturn";
- size rules shown as ranges (sash width / height), in the unit of the configuration (option to show inches);
- machining (EasyMac), warning and error fittings shown as such, not as hardware.
- STR: FP_KIT Code. DB: `kit`, `dettagliokit`, `gruppiopzkit`, `accessori`, `serie_accessori`, `accessoricollegati`.

### 3. Joinery
- Multijoint fittings: from the series `.NOD` files (Nod folder of the configuration), records whose profile A and profile B both appear in the style; list the profile pair and its fittings (code, description, quantity).
- Profile fixings: `fissaggi` rows of the profiles in the style (fitting or profile piece, quantity, cut length). Compounds use the fixings of their main profile.
- Glass node fittings in the STR (FP_FITTING under the glazing node: setting blocks, seals).

### 4. Pane tables
For each glazed opening: the glass currently in the style (8510 piece DXF) and its beads, then the pane tables that could apply: `riempimenti` / `combinazioniriempimenti` rows whose glazing room (`spazioutile`) matches the room of the surrounding profile (`profili.spazio_utile`), with glass thickness, tolerance, beads and their fittings (`accessoririempimenti`).

### 5. Machinings
`ldtaccessori` rows whose profile (serieprofilo1 / codiceprofilo1, and profile 2 when set) is in the style: machine, LDT file(s), triggering fitting, and which of the style's kits carries that fitting (or "not in any kit of this style"). Also `profcompatldt` (LDTs registered per profile).

## Implementation notes

- Port, don't import: copy the elevation renderer and PRM interpreter from `emmegisoft_fpp_customReports` (`tools/format_study/str_elevation.py`, `src/fpp_customreports/prm.py`) and the NOD reader (`tools/format_study/nod_reader.py`) into `fpptools/render/` and `fpptools/nod.py`. Keep the verified rules and their comments.
- `matplotlib` (and anything else for PDF) as an optional extra: `pip install fpptools[report]`. The base CLI must keep working without it; `str sheet` says what to install when it's missing.
- Readers pure (path/DB in, plain data out); rendering separate. All SQL in one module, SELECT only through `db.ReadOnlyDB`; must work on MySQL and Access (no MySQL-only syntax such as recursive CTEs: resolve replacement fittings in Python).
- PRM folder: `C:\FP_PRO\Prm` (and `Prm\OPEN_EXT` for external sight). Missing PRM (e.g. `MODEL-00`): draw without the symbol and note it on the sheet, never fail the whole run.
- Unknowns are shown, not guessed: anything the reader can't resolve is printed as "not resolved" on the sheet.
- Tests: generic fixtures only (small synthetic STR, NOD bytes, an in-memory/SQLite stand-in for the DB queries). No client files in the repo.
- Docs: `docs/str-sheet.md`, README link, CHANGELOG entry, version bump.

## First test set (outside the repo)

A door library with single and pair doors, standard and thermally broken, inswing and outswing (about 28 styles), on MySQL 8. Check every sheet against FP Pro's own picture of the style and the kit editor.

## Later

- `--page tabloid`; one sheet per job item (job records) instead of per style.
- Spanish/Italian labels for the sheet (same `--lang` as other commands).
