# `fpptools str sheet`

One PDF page per structure (`.STR`): the item elevation on the left and, on the right, what the library applies to it, so a style can be reviewed without opening FP Pro or the database. Read-only: it never writes STR, NOD, PRM or database data.

```powershell
pip install fpptools[report]                                     # once: adds matplotlib
fpptools str sheet --under DESA_DOORS --match "100-*" -o doors.pdf
fpptools str sheet --sight int --lang es
```

## Options

| Option | Default | |
|---|---|---|
| `--under FOLDER` | all | only that folder of the tree (either slash, case-insensitive) |
| `--match PATTERN` | all | file name without extension, `*` and `?` wildcards, case-insensitive |
| `--root FOLDER` | `STR_PATH` | scan another folder (e.g. a copy) |
| `-o`, `--out` | `str_sheets.pdf` | one multi-page PDF |
| `--page letter` | `letter` | Letter landscape (`tabloid` later) |
| `--sight int\|ext` | as stored | draw the elevation seen from inside or outside; FP mirrors it when the style was drawn for the other side |
| `--lang en\|es` | `en` | labels on the sheet |

The sheet uses the active FP Pro configuration (`FP_PRO.INI`) like the other commands: the opening symbols come from `START_PATH\Prm` (and `Prm\OPEN_EXT` for outside sight), the multijoints from `NODES_PATH`.

## Requirements

`matplotlib` is an optional extra, so the base CLI works without it: `pip install fpptools[report]`. If it is missing, the command says what to install.

**Fonts.** The look follows the emmegisoft report design. Titles use Barlow, a DIN-style open font (SIL OFL) that ships with fpptools (`fpptools/render/fonts`, licence alongside); text uses Calibri when Windows has it (never shipped), else DejaVu Sans. `FPPTOOLS_FONTS` can point at a folder with more font files.

**Database.** The database sections are read-only SELECTs on MySQL or Access, like the other commands. `--no-db` skips them (files only, faster). If the database cannot be reached, the sheet is still written and those sections say "not resolved".

## What is on a sheet

Header: style name, folder, unique code (`NameStr`), description, configuration, date, size and the side it is drawn for.

| | From the STR and NOD files | From the database (skipped with `--no-db`) |
|---|---|---|
| Elevation | Drawn from the STR: profiles, glass, ghost pieces dotted, clearance lines, opening symbols (PRM), FP-style dimensions, profile labels | |
| 1. Profiles | Use, series, code, quantity of every produced piece | Descriptions, compounds and their components |
| 2. Kits | Kits on each node: code, description, FP's raw optional / confirmed flags | Collection, hardware after replacement fittings, choices ("N options, default: X"), size ranges, machining / warning / error rows |
| 3. Joinery | Multijoint (NOD) records between the style's profiles: profile pair, fittings and quantity; glazing fittings in the style | Profile fixings (compounds use their main profile) |
| 4. Pane tables | Glass and beads in the style, pane table code | The style's pane table with its combinations, and other tables that could apply |
| 5. Machinings | | Machinings of the style's profiles (machine, LDT files, fitting) and the kit that carries each fitting; LDTs registered per profile |

Anything that cannot be resolved is printed as "not resolved" on the sheet; nothing is guessed. Hinge-type machinings are listed under "Others" (FP stores them that way). Fixing quantities are the base quantity only; FP's formula columns are not evaluated. A missing opening symbol (PRM) is drawn without it and noted; the run goes on.

Details and design: [docs/requests/str-sheet.md](https://github.com/andoresuperesu/fpptools/blob/master/docs/requests/str-sheet.md).
