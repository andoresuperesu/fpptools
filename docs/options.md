# Common options

## Configuration

| Option | |
|---|---|
| (none) | the configuration active in FP Pro: `%APPDATA%\Emmegisoft\FP_PRO\FP_PRO.INI` |
| `--ini PATH` | another FP_PRO.INI; goes **before** the command: `fpptools --ini D:\x\FP_PRO.INI str list` |
| `FPPTOOLS_INI` | environment variable, same as `--ini` |

Nothing is read until a command needs it, so `--help` and `--version` work on a PC without FP Pro.

## Choosing files (`str list`, `fit list` str/blk, `wipe`)

| Option | |
|---|---|
| `--under FOLDER` | only inside that folder, relative to the root, e.g. `019_SERIE_22_PESADO` or `LINEA SUPERIOR/SERIE 35` (either slash, case-insensitive) |
| `--match PATTERN` | file name without extension, wildcards `*` `?`, case-insensitive, e.g. `"VTA_*"` |
| `--root FOLDER` | scan this folder instead of `STR_PATH` / `BLK_PATH` / `JOB_PATH` (e.g. a copy of a configuration) |

## Output (`str list`, `fit list`)

| `-o` / `--out` | |
|---|---|
| `file.csv` | `;` separated, UTF-8 with BOM, CRLF: Excel opens it with accents and columns right (Spanish/Italian locale) |
| `file.xlsx` | Excel workbook: frozen header row, filters, column widths |
| `-` | the console (`;` separated) |

Defaults: `structures.csv`, `fittings_<source>.csv`, in the current folder. `--lang es` writes Spanish headers.

Progress bars and `warning:` lines go to the error stream (stderr), so `-o -` output can be redirected cleanly: `fpptools str list -o - > estructuras.csv`.

## General

| | |
|---|---|
| `--version` | prints the version |
| `-h`, `--help` | on every command and group: `fpptools wipe kits --help` |
| `python -m fpptools …` | same as `fpptools …` (when the command isn't on the PATH) |

Errors (INI not found, folder missing, database unreachable) print one `Error:` line, no traceback, and exit with code 1.
