"""Simulate / apply for commands that modify FP Pro files.

Simulate (default) reports what would change and writes nothing.
Apply first backs up every file it will touch, then writes each one atomically.
Backups go to <backup-dir>/<timestamp>/<path relative to the scanned root>, plus report.txt.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from fpptools.errors import FppToolsError


@dataclass
class FileChange:
    path: Path
    new_bytes: bytes
    actions: list[str] = field(default_factory=list)


@dataclass
class ChangeSet:
    root: Path
    changes: list[FileChange] = field(default_factory=list)

    def add(self, change: FileChange) -> None:
        if change.actions:
            self.changes.append(change)

    @property
    def action_count(self) -> int:
        return sum(len(c.actions) for c in self.changes)

    def report_lines(self, applied: bool) -> list[str]:
        verb = "changed" if applied else "would change"
        lines = []
        for c in self.changes:
            lines.append(os.path.relpath(c.path, self.root))
            lines.extend(f"    - {a}" for a in c.actions)
        lines.append("")
        lines.append(f"{len(self.changes)} file(s) {verb}, {self.action_count} change(s).")
        return lines


def apply(cs: ChangeSet, backup_dir: Path, header: str = "") -> Path:
    """Back up then write every changed file. Returns the backup folder."""
    root = Path(cs.root).resolve()
    backup_dir = Path(backup_dir).resolve()
    if backup_dir == root or root in backup_dir.parents:
        raise FppToolsError(
            f"Backup folder {backup_dir} is inside {root}; FP Pro would list the backups. Choose another --backup-dir."
        )
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest, n = backup_dir / stamp, 1
    while dest.exists():
        n += 1
        dest = backup_dir / f"{stamp}_{n}"
    # 1. back up everything first: if this fails, nothing has been modified
    for c in cs.changes:
        target = dest / os.path.relpath(c.path, cs.root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(c.path, target)
    # 2. write
    for c in cs.changes:
        tmp = c.path.with_name(c.path.name + ".fpptools.tmp")
        tmp.write_bytes(c.new_bytes)
        shutil.copystat(c.path, tmp)
        os.replace(tmp, c.path)
    report = ([header, ""] if header else []) + cs.report_lines(applied=True)
    (dest / "report.txt").write_text("\n".join(report) + "\n", encoding="utf-8-sig")
    return dest
