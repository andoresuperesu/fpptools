# fpptools

Administration and debugging command line for emmegisoft **FP Pro**: structures (`.STR`), blocks (`.BLK`) and job records.
It works on the configuration that is **active in FP Pro right now** (read from `%APPDATA%\Emmegisoft\FP_PRO\FP_PRO.INI`).

📖 **Full documentation:** [docs/](https://github.com/andoresuperesu/fpptools/blob/master/docs/README.md) · *Guía rápida en español más abajo.*

## Install

```powershell
pip install fpptools          # or: uv tool install fpptools
fpptools --help
```

No Python on the PC? Use the standalone exes: `fpptools.exe` (full command line) and `fpptools_estructuras.exe` (double-click: structures to `estructuras.xlsx`). See [Standalone exes](https://github.com/andoresuperesu/fpptools/blob/master/docs/exe.md).

## Commands

| Command | What it does | Docs |
|---|---|---|
| `fpptools config` | Show the active configuration: INI, folders, database (password hidden). Run it first when something isn't found | [config](https://github.com/andoresuperesu/fpptools/blob/master/docs/config.md) |
| `fpptools str list` | Structures: folder, name, unique code (*nombre unívoco*), description → `structures.csv` | [str list](https://github.com/andoresuperesu/fpptools/blob/master/docs/str-list.md) |
| `fpptools fit list` | Fittings used in structures, blocks, one job or all jobs (`--source str\|blk\|job\|jobs`), kits expanded from the database → `fittings_<source>.csv` | [fit list](https://github.com/andoresuperesu/fpptools/blob/master/docs/fit-list.md) |
| `fpptools wipe panedefs` | Remove glass fittings, glass DXF and pane table from every pane of the structures | [wipe](https://github.com/andoresuperesu/fpptools/blob/master/docs/wipe.md) |
| `fpptools wipe kits` | Remove every kit from structures or blocks (`--source str\|blk`) | [wipe](https://github.com/andoresuperesu/fpptools/blob/master/docs/wipe.md) |
| `fpptools-estructuras` | Same as `str list --lang es -o estructuras.xlsx` (what the double-click exe runs) | [exe](https://github.com/andoresuperesu/fpptools/blob/master/docs/exe.md) |
| `fpptools list_fittings` | 0.1 syntax (`--searchtype`), deprecated: use `fit list` | [fit list](https://github.com/andoresuperesu/fpptools/blob/master/docs/fit-list.md#01-syntax-list_fittings) |

**Common options** ([details](https://github.com/andoresuperesu/fpptools/blob/master/docs/options.md)):

- Choose files: `--under FOLDER`, `--match PATTERN`, `--root FOLDER`.
- Output: `-o file.csv` / `file.xlsx` / `-` (console); CSV with `;` and UTF-8 BOM (opens right in Excel); `--lang es` for Spanish headers.
- `--ini PATH` (or `FPPTOOLS_INI`): another FP_PRO.INI · `--version` · `-h` / `--help` on every command · `python -m fpptools` = `fpptools`.

**Commands that modify files only simulate** unless you add `--apply`; with `--apply` the originals are backed up first ([wipe](https://github.com/andoresuperesu/fpptools/blob/master/docs/wipe.md)).

```powershell
fpptools config
fpptools str list --lang es -o estructuras.xlsx
fpptools fit list --source blk -o fittings_blk.xlsx
fpptools wipe panedefs --under "LINEA X"            # simulation
fpptools wipe panedefs --under "LINEA X" --apply    # backup + write
```

---

## Guía rápida (español)

`fpptools` trabaja sobre la configuración **activa en FP Pro**. `fpptools config` muestra cuál es (carpetas y base de datos).

**Exportar nombre y descripción de las estructuras:**

```powershell
fpptools str list --lang es -o estructuras.xlsx
fpptools str list --under 019_SERIE_22_PESADO --lang es -o serie22.csv
```

Columnas: Carpeta, Nombre (nombre del archivo), Nombre único (nombre unívoco), Descripción.

**Sin línea de comandos:** doble clic en `fpptools_estructuras.exe`. Crea `estructuras.xlsx` en la misma carpeta del programa (si está abierto en Excel, crea `estructuras_<fecha_hora>.xlsx`). El programa debe estar en una carpeta donde se pueda escribir (no en `C:\Program Files`).

**Accesorios:** `fpptools fit list --source str|blk|job|jobs --lang es -o accesorios.xlsx`.

**Comandos que modifican archivos** (`wipe`): por defecto solo **simulan** y muestran qué cambiarían. Con `--apply` primero copian los originales a `fpptools_backups\<fecha_hora>\` y luego escriben. Cierre las estructuras en FP Pro antes de aplicar.

Documentación completa (en inglés): [docs/](https://github.com/andoresuperesu/fpptools/blob/master/docs/README.md).

## Development

See [docs/development.md](https://github.com/andoresuperesu/fpptools/blob/master/docs/development.md) (uv, tests, exes, PyPI).

License: MIT.
