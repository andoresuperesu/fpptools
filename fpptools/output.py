"""Table output: CSV that Excel opens correctly in Spanish/Italian locales, or .xlsx."""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Iterable, Sequence

CSV_DELIMITER = ";"
CSV_ENCODING = "utf-8-sig"  # BOM: Excel detects UTF-8 and shows accents correctly


def write_table(headers: Sequence[str], rows: Iterable[Sequence], out: str | Path) -> str:
    """Write rows to out ('-' = console). Returns a description of where they went."""
    rows = list(rows)
    if str(out) == "-":
        w = csv.writer(sys.stdout, delimiter=CSV_DELIMITER, lineterminator="\n")
        w.writerow(headers)
        w.writerows(rows)
        return "console"
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".xlsx":
        from openpyxl import Workbook
        from openpyxl.utils import get_column_letter

        wb = Workbook()
        ws = wb.active
        ws.title = "fpptools"
        ws.append(list(headers))
        for r in rows:
            ws.append(list(r))
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        for i, h in enumerate(headers, start=1):
            width = max([len(str(h))] + [len(str(r[i - 1])) for r in rows[:2000]])
            ws.column_dimensions[get_column_letter(i)].width = min(max(10, width + 2), 80)
        wb.save(path)
    else:
        with path.open("w", encoding=CSV_ENCODING, newline="") as f:
            w = csv.writer(f, delimiter=CSV_DELIMITER, lineterminator="\r\n")
            w.writerow(headers)
            w.writerows(rows)
    return str(path)
