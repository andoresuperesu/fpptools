# fpptools

Administration and debugging command line for emmegisoft **FP Pro**: structures (`.STR`), blocks (`.BLK`) and job records.
It works on the configuration that is **active in FP Pro right now** (read from `%APPDATA%\Emmegisoft\FP_PRO\FP_PRO.INI`).

*Guía rápida en español más abajo.*

## Install

```powershell
pip install fpptools          # or: uv tool install fpptools
fpptools --help
```

Standalone exes (no Python needed) are built with `scripts\build_exe.ps1`:

- `fpptools.exe`: the full command line.
- `fpptools_estructuras.exe`: **double-click** to export the structures of the active configuration to `estructuras.xlsx` next to the exe (same as `fpptools str list --lang es -o estructuras.xlsx`). If that file is open in Excel, it writes `estructuras_<date_time>.xlsx` instead. Also installed as the `fpptools-estructuras` command.

## Commands

| Command | What it does |
|---|---|
| `fpptools config` | Show the active configuration: folders, database (password hidden) |
| `fpptools str list` | List structures: folder, name, unique code, description |
| `fpptools fit list` | List fittings used in structures, blocks, one job or all jobs (kits expanded from the database) |
| `fpptools wipe panedefs` | Remove glass fittings, glass DXF and pane table from every pane of the structures |
| `fpptools wipe kits` | Remove every kit from structures or blocks |

Every command has `--help`.

### Choosing files

Commands that read STR/BLK folders accept:

- `--under FOLDER`: only that folder of the tree, e.g. `--under 019_SERIE_22_PESADO`
- `--match PATTERN`: file name pattern without extension, e.g. `--match "VTA_*"` (case-insensitive)
- `--root FOLDER`: another folder instead of the one in FP_PRO.INI

### Output

`--out file.csv` (default), `--out file.xlsx`, or `--out -` for the console.
CSV files use `;` and UTF-8 with BOM, so Excel opens them correctly with accents. `--lang es` writes Spanish headers.

### Commands that modify files: simulate first

`wipe` commands **only simulate** by default: they report what would change and write nothing.
Add `--apply` to write. Before writing, every file is copied to `--backup-dir` (default `.\fpptools_backups\<date_time>\`, same sub-folders) together with a `report.txt`. To undo, copy the backed-up files back.

```powershell
fpptools wipe panedefs --under "LINEA X"            # simulation
fpptools wipe panedefs --under "LINEA X" --apply    # backup + write
```

Close the structures in FP Pro before applying.

### Structure fields

| Column | Where it comes from |
|---|---|
| Folder | Folder of the file inside STR_PATH (the tree in FP Pro's structure browser) |
| Name | File name without `.STR` (the "Nombre" field in FP Pro) |
| Unique code | `FP_TREE/@NameStr` ("nombre unívoco" in FP Pro) |
| Description | `FP_TREE/FP_DESCRIPTION`, stored as Base64 inside the file |

### Database

`fit list` reads kits from the FP Pro database of the active configuration: MySQL (`CONN_STR_FP_PRO=1`, settings in `[MYSQL]`) or Access (`Fp_Pro32.MDB` in `MDB_PATH`). Queries are read-only.
Access needs the Microsoft Access ODBC driver with the same bitness (32/64-bit) as Python. Use `--no-db` to skip the database.

### Other options

- `--ini PATH` (or environment variable `FPPTOOLS_INI`): use another FP_PRO.INI.
- `fpptools list_fittings --searchtype str` (0.1 syntax) still works but is deprecated.

---

## Guía rápida (español)

`fpptools` trabaja sobre la configuración **activa en FP Pro**.

**Exportar nombre y descripción de las estructuras:**

```powershell
fpptools str list --lang es -o estructuras.xlsx
fpptools str list --under 019_SERIE_22_PESADO --lang es -o serie22.csv
```

Columnas: Carpeta, Nombre (nombre del archivo), Nombre único (nombre unívoco), Descripción.

**Sin línea de comandos:** doble clic en `fpptools_estructuras.exe`. Crea `estructuras.xlsx` en la misma carpeta del programa (si está abierto en Excel, crea `estructuras_<fecha_hora>.xlsx`). El programa debe estar en una carpeta donde se pueda escribir (no en `C:\Program Files`).

**Comandos que modifican archivos** (`wipe`): por defecto solo **simulan** y muestran qué cambiarían. Con `--apply` primero copian los originales a `fpptools_backups\<fecha_hora>\` y luego escriben. Cierre las estructuras en FP Pro antes de aplicar.

`fpptools config` muestra qué configuración, carpetas y base de datos está usando.

## Development

```powershell
uv sync
uv run pytest
uv run fpptools --help
uv build ; uv publish                     # PyPI
.\scripts\build_exe.ps1                   # dist_exe\fpptools.exe, dist_exe\fpptools_estructuras.exe (not in dist\: that is PyPI's)
```

License: MIT.
