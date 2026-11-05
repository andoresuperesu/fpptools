# `fpptools fit list`

Lists every fitting used, one row per fitting.

```powershell
fpptools fit list                                   # structures -> fittings_str.csv
fpptools fit list --source blk -o fittings_blk.xlsx
fpptools fit list --source job --job 27002_6 -o -
fpptools fit list --source jobs
fpptools fit list --under "LINEA X" --no-db
```

## `--source`

| Value | What it scans | Folder (FP_PRO.INI) | Columns |
|---|---|---|---|
| `str` (default) | every structure `.STR` | `STR_PATH` | Folder, File, Fitting, Source, Note |
| `blk` | every block `.BLK` | `BLK_PATH` | Folder, File, Fitting, Source, Note |
| `job` | the job records of one job (`--job NAME`, asked if missing) | `JOB_PATH` | Job, Item, Fitting, Source |
| `jobs` | the job records of every job | `JOB_PATH` | Job, Item, Fitting, Source |

- **Source** is the element the fitting hangs from, as `<element>:<code>` (e.g. `FP_NODE:10`), or `FP_KIT:<kit>` for fittings that come from a kit.
- **Note** says when a kit is not in the database, or when `--no-db` was used (the kit is listed but not expanded).
- Job records are found as `<JOB>_JOBRECORD*.XML` under `JOB_PATH` (as in 0.1; not yet checked on FP Pro 11).

## Kits and the database

Kits in STR/BLK files are expanded from the database of the active configuration (tables `kit` / `dettagliokit`): one row per fitting of the kit. Fittings written inside a kit in the file are not listed again.

- MySQL (`CONN_STR_FP_PRO=1`): settings from `[MYSQL]` (see [config](config.md)).
- Access (`CONN_STR_FP_PRO=0`): `Fp_Pro32.MDB` in `MDB_PATH`; needs the Microsoft Access ODBC driver with the same bitness (32/64-bit) as Python or the exe.
- Queries are read-only (SELECT only).
- `--no-db` skips the database (e.g. no access to the server).

## Options

| Option | Default | |
|---|---|---|
| `--source str\|blk\|job\|jobs` | `str` | see above |
| `--job NAME` | asked | job for `--source job` |
| `--no-db` | off | don't read the database; kits listed, not expanded |
| `--under`, `--match`, `--root` | | `str` and `blk` only, see [options](options.md) |
| `-o`, `--out` | `fittings_<source>.csv` | `.csv`, `.xlsx` or `-` |
| `--lang en\|es` | `en` | column headers |

A file that can't be read gets a row with the reason in **Note** and a `warning:` line; the rest goes on.

## 0.1 syntax (`list_fittings`)

`fpptools list_fittings --searchtype str|blk|job|jobs [--tofile y|n] [--verbose y|n]` still works (hidden, deprecated; it prints a reminder):

| 0.1 | Now |
|---|---|
| `--searchtype X` | `fit list --source X` |
| `--tofile y` (default) | writes `fittinglist_<X>.csv` |
| `--verbose y` (or `--tofile n`) | prints to the console (`-o -`) |
