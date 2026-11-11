# fpptools documentation

fpptools works on the FP Pro configuration that is **active right now** (`%APPDATA%\Emmegisoft\FP_PRO\FP_PRO.INI`): its folders (`STR_PATH`, `BLK_PATH`, `JOB_PATH`) and its database.

| Page | Contents |
|---|---|
| [config](config.md) | `fpptools config`: which configuration, folders and database fpptools will use |
| [str list](str-list.md) | Structures: folder, name, unique code, description (the Estructura browser) |
| [str sheet](str-sheet.md) | PDF sheet per structure: elevation, profiles, kits, joinery (`pip install fpptools[report]`) |
| [fit list](fit-list.md) | Fittings in structures, blocks and job records; kits from the database; the 0.1 `list_fittings` syntax |
| [wipe](wipe.md) | `wipe panedefs`, `wipe kits`: simulation, `--apply`, backups, reports |
| [options](options.md) | Options common to all commands: choosing files, output formats, `--ini`, `--version`, errors |
| [exe](exe.md) | Standalone `fpptools.exe` and the double-click `fpptools_estructuras.exe` |
| [development](development.md) | uv, tests, building the exes, publishing to PyPI |

Every command also explains itself: `fpptools <command> --help` (e.g. `fpptools fit list --help`).
