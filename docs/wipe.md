# `fpptools wipe`

Commands that **modify** FP Pro files. They **only simulate** unless you add `--apply`.

| Command | Files | What is removed |
|---|---|---|
| `wipe panedefs` | structures (`.STR`) | from every pane (`FP_NODE ElementType="8650"`): its glass fittings (`FP_FITTING` directly under the pane), the glass DXF (`DXF` of `FP_PIECE Type="8510"`) and the pane table (`PaneTableCode`). Leaves a reusable base that can't be used without re-checking glass and pane table |
| `wipe kits` | structures (`--source str`, default) or blocks (`--source blk`) | every kit (`FP_KIT` with its content) |

```powershell
fpptools wipe panedefs --under "LINEA X"                       # simulation
fpptools wipe panedefs --under "LINEA X" --report informe.txt  # simulation, report saved
fpptools wipe panedefs --under "LINEA X" --apply               # backup + write
fpptools wipe kits --source blk --match "BLK_OLD_*" --apply
```

**Close the structures/blocks in FP Pro before `--apply`.**

## Simulation (default)

Prints, per file, what would change (e.g. `pane 7: glass DXF GLASSES\ST4_4.DXF removed`) and the total:
`703 file(s) would change, 6826 change(s).` Nothing is written. `--report FILE` also saves that report to a file (UTF-8). With nothing to change: `Nothing to change in N file(s).`

## `--apply`

1. **Backup first:** every file that will change is copied to `--backup-dir` (default `.\fpptools_backups`, in the current folder) under a new `<YYYYMMDD_HHMMSS>\` folder, keeping its sub-folders, together with `report.txt`. If the backup can't be made, nothing is written.
2. **Then write:** each file is written to a temporary file and swapped in.
3. **FP Pro's format is kept:** XML declaration, windows-1252, line endings (also inside CDATA), `<X/>` vs `<X />` and `<X></X>` as in the original. Only the lines of the removed parts change; an untouched file stays byte-identical.

The backup folder **can't be inside the scanned folder** (FP Pro would list the backups as structures): fpptools refuses and asks for another `--backup-dir`.

**To undo:** copy the files from the backup folder back over the originals (same sub-folders).

## Options

| Option | Default | |
|---|---|---|
| `--apply` | off | write (after the backup) |
| `--backup-dir DIR` | `fpptools_backups` | where `--apply` copies the originals |
| `--report FILE` | none | save the simulation report |
| `--source str\|blk` | `str` | `wipe kits` only |
| `--under`, `--match`, `--root` | | see [options](options.md) |

A file that can't be parsed is skipped with a `warning:` line; the others go on.
