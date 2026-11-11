"""Reader for FP Pro multijoint files (.NOD, header FILE_VERSION=0005). Read-only.

Ported from customReports tools/format_study/nod_reader.py. Layout as decoded so far (little-endian, packed):
File = b'FILE_VERSION=0005' + joint records until EOF.

Joint record = 4-byte prefix + 339-byte body + nfit * 400-byte fitting blocks
  prefix   uint16 p1, uint16 p2                (meaning unknown; (1,2) most common)
  body+0   char[41] DXF of profile A  (series\\code.DXF)
  body+41  uint16   use code of A (= profile 'use' / piece Type: 8050 frame, 8090 sash, 8180 bead ...)
  body+43  char[41] DXF of profile B
  body+84  uint16   use code of B
  body+86  char[36] optional third profile (DXF) involved in the joint, else empty
  body+300 char[37] optional DXF (second variant / reference profile), else empty
  body+337 uint16   nfit = number of fitting blocks that follow
Fitting block (400 bytes): +0 brand char[30], +30 series char[30], +60 code char[30], +90 description char[100],
  +190 category char[30], then (FppFileManagerNod.dll FITTING_RECORD_LD, int16): +220 Type (1, 4, 10),
  +228 Multiply = quantity (negative values exist, ~0.5 %: kept as stored, not interpreted), +232 RefDim,
  +266 CalcDim (3 perimeter, 5 formula). Other fields of the block are not read.

The geometry floats (80-bit extended, body+102..217) are not read: the sheet does not need them.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

MAGIC = b"FILE_VERSION=0005"


def _cstr(b: bytes) -> str:
    return b.split(b"\0", 1)[0].decode("cp1252", "replace")


def _u16(b: bytes, o: int) -> int:
    return int.from_bytes(b[o:o + 2], "little")


def _i16(b: bytes, o: int) -> int:
    return int.from_bytes(b[o:o + 2], "little", signed=True)


def _fitting(b: bytes) -> dict:
    return {"brand": _cstr(b[0:30]), "series": _cstr(b[30:60]), "code": _cstr(b[60:90]),
            "description": _cstr(b[90:190]), "category": _cstr(b[190:220]),
            "type": _i16(b, 220), "quantity": _i16(b, 228), "ref_dim": _i16(b, 232), "calc_dim": _i16(b, 266)}


def records(path: Path) -> Iterator[dict]:
    """Joint records: a, b (DXF 'series\\code.DXF'), use_a, use_b, third, variant, fittings=[{brand,series,code,
    description,category}]. Raises ValueError when the file does not follow the known layout."""
    d = Path(path).read_bytes()
    if not d.startswith(MAGIC):
        raise ValueError(f"not a FILE_VERSION=0005 NOD: {d[:20]!r}")
    i = len(MAGIC)
    while i + 343 <= len(d):
        body = d[i + 4:i + 343]
        n = _u16(body, 337)
        fits = [_fitting(d[i + 343 + k * 400:i + 343 + (k + 1) * 400]) for k in range(n)]
        yield {"a": _cstr(body[0:41]), "use_a": _u16(body, 41), "b": _cstr(body[43:84]), "use_b": _u16(body, 84),
               "third": _cstr(body[86:122]), "variant": _cstr(body[300:337]), "fittings": fits}
        i += 343 + 400 * n
    if i != len(d):
        raise ValueError(f"{path}: {len(d) - i} trailing bytes - layout assumption broken")
