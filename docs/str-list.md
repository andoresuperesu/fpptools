# `fpptools str list`

Lists the structures (`.STR`) of `STR_PATH`: the same data as FP Pro's **Estructura** browser.

```powershell
fpptools str list                                               # -> structures.csv
fpptools str list --lang es -o estructuras.xlsx
fpptools str list --under 019_SERIE_22_PESADO --match "VTA_*" -o -
```

## Columns

| Column (`--lang es`) | Where it comes from |
|---|---|
| Folder (Carpeta) | folder of the file inside `STR_PATH` (the tree in the browser), e.g. `019_SERIE_22_PESADO\VENTANA_PROYECTABLE_S22` |
| Name (Nombre) | file name without `.STR` (the "Nombre" field in FP Pro) |
| Unique code (Nombre único) | `FP_TREE/@NameStr` (FP Pro's "nombre unívoco"). Not enforced unique: two structures can share it, and it can be empty |
| Description (Descripción) | `FP_TREE/FP_DESCRIPTION`, stored as Base64 inside the file and decoded |
| Error | only when some file couldn't be read: the reason, on that file's row |

Facade structures (`FP_FACADE` files) are included.

## Options

| Option | Default | |
|---|---|---|
| `--under FOLDER` | all | only that folder of the tree (either slash, case-insensitive) |
| `--match PATTERN` | all | file name without extension, `*` and `?` wildcards, case-insensitive |
| `--root FOLDER` | `STR_PATH` | scan another folder (e.g. a copy) |
| `-o`, `--out` | `structures.csv` | `.csv`, `.xlsx` or `-` (console) |
| `--lang en\|es` | `en` | column headers |

See [options](options.md) for the output format.

## When a file can't be read

The export goes on: the row is kept with an **Error** column, and a `warning:` line is printed for each such file. The summary at the end says how many had errors.

For a double-click export without the command line, see [`fpptools_estructuras.exe`](exe.md).
