# Development

```powershell
uv sync                     # .venv with the dev group (pytest)
uv run pytest
uv run fpptools --help
```

- Python ≥ 3.10, packaging with uv + hatchling. The version is in `fpptools/__init__.py`; record changes in `CHANGELOG.md`.
- Tests use generic fixtures only (`tests/conftest.py`), never client files.
- Layout and rules for contributors (and Claude): [`CLAUDE.md`](../CLAUDE.md).

## Standalone exes

```powershell
.\scripts\build_exe.ps1     # dist_exe\fpptools.exe, dist_exe\fpptools_estructuras.exe
```

PyInstaller (`build` dependency group), one file each, console. They go to `dist_exe\`, **not** `dist\`, because `dist\` is for PyPI. The entry scripts are `scripts\exe_*.py` (outside the package on purpose).

## PyPI

```powershell
uv build                                                      # dist\fpptools-X.Y.Z.tar.gz + .whl
uv publish --keyring-provider subprocess --username __token__ dist\fpptools-X.Y.Z*
```

uv may still show a `password` prompt: press Enter without typing anything, and it uses the token from the keyring.

**The PyPI token** is a token scoped to the `fpptools` project only, kept in the Windows Credential Manager through
`keyring`, so it never appears in a command, a file or the shell history. One-time setup:

```powershell
uv tool install keyring
keyring set https://upload.pypi.org/legacy/ __token__        # paste the token when asked (not echoed)
```

Never put the token in `pyproject.toml`, the repo, a `.env` or a script, or pass it with `--token` (PowerShell keeps
typed commands in its history file). To replace it: revoke it on PyPI (Account settings → API tokens), create a new one
for the project, run `keyring set …` again.


- A published version can't be replaced: fix → bump the version.
- The README is the PyPI page: links to these docs are absolute GitHub links.
- Keep the package name `fpptools`, the `fpptools` command and old commands (hidden aliases when renaming).
