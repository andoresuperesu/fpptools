# Standalone exes

For PCs without Python. Built with `scripts\build_exe.ps1` (see [development](development.md)) into `dist_exe\`; sent separately, not on PyPI.

| Exe | |
|---|---|
| `fpptools.exe` | the full command line: `fpptools.exe str list --lang es -o estructuras.xlsx`, `fpptools.exe config`… |
| `fpptools_estructuras.exe` | **double-click**: exports the structures of the active configuration to `estructuras.xlsx` **next to the exe** |

## `fpptools_estructuras.exe`

Same as `fpptools str list --lang es -o estructuras.xlsx` (columns in [str list](str-list.md)), for users who don't use the command line:

- Takes the configuration active in FP Pro.
- Writes `estructuras.xlsx` in the exe's folder; if that file is open in Excel, writes `estructuras_<YYYYMMDD_HHMMSS>.xlsx` instead.
- The window stays open at the end (`Pulse Enter para cerrar…`) with `Listo: <file>` or the error.
- The exe must be in a folder where the user can write (not `C:\Program Files`).
- With Python installed, the same is the `fpptools-estructuras` command.
