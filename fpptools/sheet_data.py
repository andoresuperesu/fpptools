"""Data for one style sheet (`fpptools str sheet`): plain dataclasses, filled by pure readers.

CONTRACT shared by the readers (this module) and the renderer (fpptools/render/sheet.py):
- Anything the reader cannot resolve is left empty / None and the renderer prints "not resolved" (never guessed).
- Phase 1 reads the STR (and NOD files) only. Database-backed fields (descriptions, kit contents, fixings, pane
  tables, machinings) stay empty and the sheet says "not read yet" for them.
"""

from __future__ import annotations

import functools
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

from fpptools import nod, strfile

# Piece use codes -> readable name (vault FPProFileFormats/04). Unknown codes print as "Use <code>".
USE_NAMES = {
    "8050": "Frame", "8060": "Mullion", "8070": "Transom", "8090": "Casement sash", "8100": "Sliding sash",
    "8101": "Sliding sash, fixed", "8110": "Use 8110", "8130": "Sill", "8170": "Multi-purpose profile",
    "8180": "Glazing bead", "8210": "Sliding interlock", "8270": "Panel bead", "8280": "Rail", "8500": "Panel",
}
# Node ElementType -> readable name (hinged sash 8610 etc., vault FPProFileFormats/04). Unknown: "Node <type>".
NODE_NAMES = {"8600": "Frame", "8610": "Hinged sash", "8620": "Sliding sashes", "8630": "Folding sash",
              "8650": "Glazing"}


@dataclass
class ProfileRow:
    use: str            # piece Type code, e.g. "8050"
    series: str         # DXF folder, e.g. "DESA_DOORS"
    code: str           # DXF file stem
    qty: int            # produced pieces in the style (ghosts and clearance excluded)


@dataclass
class KitRow:
    code: str
    description: str
    optional: bool      # FP_KIT Optional="1" (raw flag, meaning not documented)
    confirmed: bool     # FP_KIT Confirmed="1" (raw flag, meaning not documented)
    multiply: str


@dataclass
class KitGroup:
    node_type: str      # ElementType of the node that carries the kits ("" = style root)
    node_code: str
    kits: list[KitRow] = field(default_factory=list)


@dataclass
class GlazingFitting:   # FP_FITTING under a glazing node (outside kits)
    code: str
    description: str
    type: str
    multiply: str
    openings: list[str] = field(default_factory=list)   # node Codes (the numbers FP shows)


@dataclass
class PaneRow:
    openings: list[str]
    glass: str          # 8510 piece DXF stem, e.g. "06MM"
    beads: str          # e.g. "SQSTOP1+SQSTOP1 x4"; "" when none
    pane_table: str     # PaneTableCode (a GUID; phase 2 resolves it), "" if none


@dataclass
class JointRow:
    profile_a: str      # "SERIES\\CODE"
    profile_b: str
    fittings: list[tuple[str, str, int]]   # (code, description, quantity = NOD Multiply) from the NOD record


@dataclass
class SheetData:
    path: Path
    folder: str
    name: str
    unique_code: str
    description: str
    side: str                       # "ext" | "int": the side the style is drawn for ($$EXT$$)
    size: tuple[float, float] | None = None       # reference outline W x H in model units (mm), or None
    profiles: list[ProfileRow] = field(default_factory=list)
    kits: list[KitGroup] = field(default_factory=list)
    glazing_fittings: list[GlazingFitting] = field(default_factory=list)
    panes: list[PaneRow] = field(default_factory=list)
    joints: list[JointRow] = field(default_factory=list)     # NOD joints with fittings between style profiles
    joints_without_fittings: int = 0                         # NOD joints between style profiles with none
    nod_checked: bool = False       # False = no NOD folder / unreadable -> "not resolved"
    notes: list[str] = field(default_factory=list)           # reader warnings shown on the sheet
    error: str = ""
    # phase 2: filled by fpptools/sheetdb (package, one module per section); None = database not read
    db: object | None = None


# -- readers ------------------------------------------------------------------------------------------------
# Pure: path in, plain data out. No matplotlib, no database.

def _stem(dxf: str) -> str:
    name = dxf.replace("/", "\\").rsplit("\\", 1)[-1]
    return name.rsplit(".", 1)[0] if "." in name else name


def _series(dxf: str) -> str:
    d = dxf.replace("/", "\\")
    return d.rsplit("\\", 1)[0] if "\\" in d else ""


def _profile_key(dxf: str) -> str:
    return dxf.replace("/", "\\").strip().casefold()


@functools.lru_cache(maxsize=64)
def _load_nod(path: str, mtime: float) -> tuple:
    return tuple(nod.records(Path(path)))


def _nod_records(path: Path) -> tuple:
    return _load_nod(str(path), path.stat().st_mtime)


def read_sheet(path: Path, root: Path, nod_dir: Path | None = None) -> SheetData:
    """Everything the sheet needs from one STR (plus the NOD folder for joinery). Never raises for bad files:
    `error` is set instead."""
    path = Path(path)
    info = strfile.read_info(path, root)
    data = SheetData(path=path, folder=info.folder, name=info.name, unique_code=info.unique_code,
                     description=info.description, side="int", error=info.error)
    try:
        text = path.read_bytes().decode(strfile.ENCODING, errors="replace")
        data.side = "ext" if re.search(r'VarName="\$\$EXT\$\$" VarValue="1', text) else "int"
        xml_root = ET.fromstring(re.sub(r"^<\?xml[^>]*\?>", "", text.lstrip("﻿")))
    except (ET.ParseError, OSError) as exc:
        data.error = data.error or f"cannot read: {exc}"
        return data
    tree = xml_root if xml_root.tag == "FP_TREE" else xml_root.find(".//FP_TREE")
    if tree is None:
        data.error = data.error or "no FP_TREE element"
        return data

    parent = {c: p for p in tree.iter() for c in p}

    def ancestor(el, tag):
        p = parent.get(el)
        while p is not None and p.tag != tag:
            p = parent.get(p)
        return p

    pv = tree.find("FP_PREVIEW")
    if pv is not None:
        pts = [(float(v.get("x")), float(v.get("y"))) for v in pv.findall("FP_PATH_VERTEX")]
        if pts:
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            data.size = (max(xs) - min(xs), max(ys) - min(ys))

    # profiles: produced pieces only (no glass, no clearance, no ghosts), grouped by use + DXF
    counts: dict[tuple[str, str], int] = {}
    for pc in tree.iter("FP_PIECE"):
        if pc.get("Type") in ("8510", "8040") or pc.get("ElementGhost") == "1" or ancestor(pc, "FP_KIT") is not None:
            continue
        key = (pc.get("Type") or "", pc.get("DXF") or "")
        counts[key] = counts.get(key, 0) + 1
    for (use, dxf), n in counts.items():
        data.profiles.append(ProfileRow(use, _series(dxf), _stem(dxf), n))

    # kits per carrying node
    groups: dict[tuple[str, str], KitGroup] = {}
    for kit in tree.iter("FP_KIT"):
        node = ancestor(kit, "FP_NODE")
        key = (node.get("ElementType") or "", node.get("Code") or "") if node is not None else ("", "")
        g = groups.setdefault(key, KitGroup(*key))
        g.kits.append(KitRow(kit.get("Code") or "", kit.get("Description") or "", kit.get("Optional") == "1",
                             kit.get("Confirmed") == "1", kit.get("Multiply") or ""))
    data.kits = list(groups.values())

    # glazing nodes: fittings (outside kits) and panes
    gf: dict[tuple[str, str, str, str], GlazingFitting] = {}
    panes: dict[tuple[str, str, str], PaneRow] = {}
    for node in tree.iter("FP_NODE"):
        if node.get("ElementType") != "8650":
            continue
        code = node.get("Code") or ""
        for ft in node.iter("FP_FITTING"):
            if ancestor(ft, "FP_KIT") is not None or ancestor(ft, "FP_NODE") is not node:
                continue
            key = (ft.get("Code") or "", ft.get("Description") or "", ft.get("Type") or "", ft.get("Multiply") or "")
            row = gf.setdefault(key, GlazingFitting(*key))
            if code not in row.openings:
                row.openings.append(code)
        pieces = [p for p in node.findall("FP_PIECE") if p.get("ElementGhost") != "1"]
        glass = next((_stem(p.get("DXF") or "") for p in pieces if p.get("Type") == "8510"), "")
        bead_n: dict[str, int] = {}
        for p in pieces:
            if p.get("Type") != "8510":
                s = _stem(p.get("DXF") or "")
                bead_n[s] = bead_n.get(s, 0) + 1
        beads = ", ".join(f"{s} x{n}" for s, n in bead_n.items())
        if not glass and not beads:
            continue
        pkey = (glass, beads, node.get("PaneTableCode") or "")
        prow = panes.setdefault(pkey, PaneRow([], *pkey))
        if code not in prow.openings:
            prow.openings.append(code)
    data.glazing_fittings = list(gf.values())
    data.panes = list(panes.values())

    # joinery from the series NOD files
    if nod_dir and Path(nod_dir).is_dir():
        files = sorted(p for p in Path(nod_dir).iterdir() if p.suffix.upper() == ".NOD")
        mine = {_profile_key(dxf) for _, dxf in counts if dxf}
        seen: set[tuple] = set()
        ok = bool(files)
        for f in files:
            try:
                recs = _nod_records(f)
            except (ValueError, OSError) as exc:
                data.notes.append(f"NOD {f.name}: {exc}")
                ok = False
                continue
            for r in recs:
                if _profile_key(r["a"]) in mine and _profile_key(r["b"]) in mine:
                    fits = [(x["code"], x["description"], x["quantity"]) for x in r["fittings"]]
                    key = (_profile_key(r["a"]), _profile_key(r["b"]), tuple(fits))
                    if key in seen:
                        continue
                    seen.add(key)
                    if fits:
                        data.joints.append(JointRow(r["a"], r["b"], fits))
                    else:
                        data.joints_without_fittings += 1
        data.nod_checked = ok
    return data
