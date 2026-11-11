"""Multilayer-aware elevation renderer for FP styles (.STR). Read-only on inputs.

Ported from customReports tools/format_study/str_elevation.py (view-stack / BMP-comparison parts dropped).

Rules (vault FPProFileFormats/06):
- root FP_PREVIEW holds polygons only for the root tree's own pieces (frame); each FP_TREE_LAYERn has its own
  FP_PREVIEW + FP_PATH_VERTEX outline, one polygon per non-glass piece of that layer (ghosts included), in order.
- layer 1 is the front, layer n the back (Andres, confirmed). FP's picture is a fixed cutaway: front layer below a
  slanted line, the layer behind above it.
- ghost pieces (ElementGhost=1) are drawn but not produced: dotted/faint, and they still count in the size of
  their opening for PRM symbols.
- PRM array vars are flattened in the STR (TYPE_SC1 -> TYPE_SC[1]).
- view side: a style is drawn for one side. Root FP_PREVIEW var `$$EXT$$`=1 -> drawn for the external view, absent ->
  internal (844/844 vs 278/278 styles). FP mirrors the picture only when the style side != the wanted side;
  mirrored hinged-sash (8610) opening lines are dashed (they open away from the viewer).
"""

from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET

from matplotlib.patches import Polygon
from matplotlib.transforms import Affine2D

from fpptools.render.prm import PRM

LAYER_TAGS = tuple(f"FP_TREE_LAYER{i}" for i in range(1, 10))

# fpptools design language (customReports docs/10): pastel fills, COOL outlines, never full-strength fills.
COOL = "#4C4D53"
FILL = {"8050": "#CDCED1", "8060": "#E0E3E5", "8070": "#E0E3E5",
        "8090": "#F5A9AF", "8100": "#F5A9AF", "8101": "#FBD9DC",
        "8180": "#FFFFFF", "8270": "#FFFFFF", "8210": "#C4C9CD", "8170": "#E6D7B8", "8130": "#CDCED1",
        # stick facades: 8320/8330 ext./int. facade mullion, 8340/8350 ext./int. facade separating rail
        "8320": "#B9BEC2", "8330": "#C8CCCF", "8340": "#D5D8DA", "8350": "#E0E3E5", "8500": "#E9E4D8"}
FILL_OTHER = "#EEEEEE"
GLASS = "#F4F5F6"
CLEAR = "#c2185b"  # clearance (8040) dotted line: distinct colour so it reads over profile edges


def own_iter(tree, tag):
    stack = list(tree)
    while stack:
        e = stack.pop(0)
        if e.tag in LAYER_TAGS:
            continue
        if e.tag == tag:
            yield e
        stack[0:0] = list(e)


def parse_text(text: str):
    """FP file text (already decoded) -> (xml root, FP_TREE)."""
    root = ET.fromstring(re.sub(r"^<\?xml[^>]*\?>", "", text))
    t = root if root.tag == "FP_TREE" else root.find(".//FP_TREE")
    return root, t


def style_side(text: str) -> str:
    return "ext" if re.search(r'VarName="\$\$EXT\$\$" VarValue="1', text) else "int"


def clearance_net(tree):
    """piece id -> net clearance gap on its edge.
    A clearance node (8040) has 4 FP_IRD, one per edge of its opening in the order left, top, right, bottom; Gap > 0
    leaves a gap, Gap < 0 protrudes past the reference. It owns one FP_PIECE per edge with a non-zero gap, in that
    edge order (13/13 job records). Consecutive clearance nodes (parent -> child) add up per edge."""
    out = {}
    parent = {c: p for p in tree.iter() for c in p}

    def is_cl(n):
        return n is not None and n.tag == "FP_NODE" and n.get("ElementType") == "8040"

    for n in own_iter(tree, "FP_NODE"):
        if not is_cl(n) or is_cl(parent.get(n)):
            continue
        chain = [n]
        while True:
            nxt = next((c for c in chain[-1] if is_cl(c)), None)
            if nxt is None:
                break
            chain.append(nxt)
        gaps = [[float(i.get("Gap") or 0) for i in m.findall("FP_IRD")][:4] for m in chain]
        net = [sum(g[k] for g in gaps if len(g) > k) for k in range(4)]
        for m, g in zip(chain, gaps):
            edges = [k for k, v in enumerate(g) if v]
            for k, pc in zip(edges, [pc for pc in m.findall("FP_PIECE") if pc.get("Type") == "8040"]):
                out[id(pc)] = net[k]
    return out


def collect(tr, prmdir, log, name, mirror=False):
    """One tree (root or layer) -> dict(items=[(kind, pts, style)], outline=[pts], glass..., ...)"""
    items = []
    pv = tr.find("FP_PREVIEW")
    if pv is None:
        log.append(f"{name}: no preview")
        return dict(items=items, outline=[], glass=False, glass_ins=[], glass_nodes=[], glass_rects=[])
    outline = [(float(v.get("x")), float(v.get("y"))) for v in pv.findall("FP_PATH_VERTEX")]
    polys = [[(float(v.get("x")), float(v.get("y"))) for v in pp.findall("FP_VERTEX")]
             for pp in pv.findall("FP_PREV_PIECE")]
    allp = list(own_iter(tr, "FP_PIECE"))
    has_glass = any(p.get("Type") == "8510" for p in allp)
    pieces = [p for p in allp if p.get("Type") != "8510"]
    log.append(f"{name}: {len(polys)} polygons / {len(pieces)} pieces "
               f"({sum(p.get('ElementGhost') == '1' for p in pieces)} ghost)")
    clear_net = clearance_net(tr)
    # glass: every glass node (8650 with an 8510 piece) carries xinsert/yinsert = the point where the fill was
    # inserted, which lies inside its opening (not necessarily the centre). glass_cells() turns each point into
    # the visible opening.
    glass_nodes = [n for n in own_iter(tr, "FP_NODE")
                   if n.get("xinsert") and any(g.get("Type") == "8510" for g in n.findall("FP_PIECE"))]
    glass_ins = [(float(n.get("xinsert")), float(n.get("yinsert"))) for n in glass_nodes]
    poly_of = {}
    for p, poly in zip(pieces, polys):
        poly_of[id(p)] = poly
        # clearance (8040, 'Aria') pieces have no width: FP stores them as 2-point polygons (a line). They are a gap
        # left on purpose to match the reference width and the module/chamber geometry. FP draws them as a dotted
        # line on top; they still size the PRM symbols. Drawn only where the NET gap is not 0: nested clearance
        # nodes add up per edge, and FP hides edges that cancel (a leftover FP writes as preview lines).
        if p.get("Type") == "8040" or len(poly) < 3:
            if clear_net.get(id(p), 1):
                items.append(("clear", poly, dict(ghost=False)))
            continue
        items.append(("poly", poly, dict(ghost=p.get("ElementGhost") == "1",
                                         fill=FILL.get(p.get("Type"), FILL_OTHER), piece=p)))
    base = dict(outline=[outline] if outline else [], glass=has_glass, glass_ins=glass_ins,
                glass_nodes=glass_nodes, glass_rects=[])
    if not prmdir:
        return dict(items=items, **base)
    hnd = {v.get("VarName").split("@@")[-1]: float(v.get("VarValue"))
           for v in pv.findall("FP_VAR") if v.get("VarName", "").startswith("HND@@")}
    for node in own_iter(tr, "FP_NODE"):
        for pr in node.findall("FP_PRM"):
            own = [p for p in node.findall("FP_PIECE") if id(p) in poly_of]  # ghosts count for the opening size
            if not own:
                continue
            ghost_node = all(p.get("ElementGhost") == "1" for p in own)
            xs = [x for p in own for x, _ in poly_of[id(p)]]
            ys = [y for p in own for _, y in poly_of[id(p)]]
            x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
            v_ = {v.get("VarName").upper(): float(v.get("VarValue")) for v in pr.iter("FP_PRM_VAR")}
            for k, v in list(v_.items()):
                m = re.match(r"^([A-Z_]+?)(\d+)$", k)
                if m:
                    v_.setdefault(m.group(1), {})[int(m.group(2))] = v
            v_["L"], v_["H"] = x1 - x0, y1 - y0
            ns = len(node.findall(".//FP_MACRO_SASH"))
            if ns:
                v_["NA"] = ns
                v_["ADIM"] = {k + 1: (x1 - x0) / ns for k in range(ns)}
                for a, v in (("Y1", 0), ("Y2", y1 - y0), ("Y3", y1 - y0), ("Y4", 0)):
                    v_[a] = {k + 1: v for k in range(ns)}
            v_["HND"] = hnd.get(node.get("Code"), 0)
            mac = node.find(".//FP_MACRO")
            if mac is not None and "PA" not in v_ and int(mac.get("MainSashIndex", -1)) >= 0:
                # 0-based main sash -> PRM's 1-based PA (LX-03 3X+1X: index 2 -> PA 3). Verified on folding doors
                # and one sliding macro; whether it holds for every macro is open.
                v_["PA"] = int(mac.get("MainSashIndex")) + 1
            prm = PRM(prmdir if isinstance(prmdir, list) else [prmdir])
            if prm.find(pr.get("Name")) is None:
                log.append(f"missing PRM {pr.get('Name')}")
                continue
            try:
                prm.run(pr.get("Name"), v_, x0, y0)
            except Exception as e:  # a broken symbol must not stop the sheet
                log.append(f"PRM {pr.get('Name')} failed: {e}")
                continue
            for kind, pts, lw, ls in prm.prims:
                # line style as the PRM sets it (LINESTYLE 0 = solid). Viewed from the other side (mirrored), FP
                # dashes the opening lines of hinged sashes (8610): they open away from the viewer. Sliding arrows
                # (8620) and fill patterns (8500/8650) keep their style.
                dashed = ls != 0 or (mirror and node.get("ElementType") == "8610")
                items.append((kind, pts, dict(ghost=ghost_node, heavy=lw >= 10, dashed=dashed)))
    return dict(items=items, **base)


def bbox(pts):
    xs = [x for x, _ in pts]
    ys = [y for _, y in pts]
    return min(xs), min(ys), max(xs), max(ys)


def paint(ax, d, clip=None, tr=None, faint=False, z=0, opaque=False):
    """Draw one collected tree d. Glass is filled only over outlines of trees that own glass (8510);
    opaque=True first blanks the outline (a back layer must hide what the front layer would show)."""
    T = (tr or Affine2D()) + ax.transData
    arts = []
    cl = [p for k, pts, _ in d["items"] if k == "clear" for p in pts]
    for o in d.get("outline", []):
        if opaque:
            arts.append(ax.add_patch(Polygon(o, fc="white", ec="none", zorder=z + 0.3)))
        if d.get("glass") and not d.get("glass_rects"):
            g_ = o
            if cl and not opaque:  # root: fill only inside its clearance lines, the gaps stay empty
                ox0, oy0, ox1, oy1 = bbox(o)
                cx0, cy0, cx1, cy1 = bbox(cl)
                x0_, y0_, x1_, y1_ = max(ox0, cx0), max(oy0, cy0), min(ox1, cx1), min(oy1, cy1)
                g_ = [(x0_, y0_), (x1_, y0_), (x1_, y1_), (x0_, y1_)]
            arts.append(ax.add_patch(Polygon(g_, fc=GLASS, ec="none", alpha=0.5 if faint else 1, zorder=z + 0.5)))
    for gr in d.get("glass_rects", []):
        arts.append(ax.add_patch(Polygon(gr, fc=GLASS, ec="#A6ACB0", lw=0.4,
                                         alpha=0.5 if faint else 1, zorder=z + 0.5)))
    for kind, pts, st in d["items"]:
        g = st.get("ghost")
        if kind == "poly":
            arts.append(ax.add_patch(Polygon(pts, fc="none" if g else st["fill"], ec="#aaa" if g else COOL, lw=0.5,
                                             ls=(0, (2, 2)) if g else "-", alpha=0.45 if faint else 1,
                                             zorder=z + (1 if g else 2))))
        elif kind == "clear":
            arts += ax.plot([p[0] for p in pts], [p[1] for p in pts], color=CLEAR, lw=0.9, ls=(0, (1.5, 1.2)),
                            zorder=z + 8)
        elif kind == "line":
            arts += ax.plot([p[0] for p in pts], [p[1] for p in pts], color="#999" if g else COOL,
                            lw=1.6 if st.get("heavy") else 0.5, ls=(0, (6, 3)) if st.get("dashed") else "-",
                            alpha=0.5 if faint else 1, zorder=z + 5)
        elif kind in ("box", "rect"):
            arts.append(ax.add_patch(Polygon(pts, fc=COOL if kind == "box" else "none", ec=COOL, lw=0.5,
                                             alpha=0.5 if faint else 1, zorder=z + 5)))
    for a in arts:
        a.set_transform(T)
        if clip is not None:
            a.set_clip_path(clip)


def _dim(ax, a, b, at, horizontal, text=None, fs=6):
    """One dimension segment from a to b (data coords) drawn at offset line `at`."""
    if abs(b - a) < 0.05:
        return
    # arrows/text don't extend the view by themselves
    ax.update_datalim([(a, at), (b, at)] if horizontal else [(at, a), (at, b)])
    arrow = dict(arrowstyle="<->", lw=0.5, shrinkA=0, shrinkB=0)
    if horizontal:
        ax.annotate("", xy=(a, at), xytext=(b, at), arrowprops=arrow, zorder=30)
        ax.text((a + b) / 2, at, text or f"{abs(b - a):.1f}", ha="center", va="bottom", fontsize=fs, zorder=31)
    else:
        ax.annotate("", xy=(at, a), xytext=(at, b), arrowprops=arrow, zorder=30)
        ax.text(at, (a + b) / 2, text or f"{abs(b - a):.1f}", ha="right", va="center", rotation=90, fontsize=fs,
                zorder=31)


def outline_ref(ax, root, mirror=False, layers=()):
    """FP-style dimensions (as FP's own elevation):
    bottom: chain through the reference width and the clearance lines (e.g. 47 / 995 / 5) + overall total (1047);
    right: same in height (14 / 1978 / 8) + total (2000, or 2057 when the module protrudes);
    left: separating-rail axes from the reference bottom (800 / 1200); top: vertical rails / mullion axes if any.
    'left/right' are visual: in a mirrored view the x axis is inverted afterwards, so the data side is swapped."""
    for o in root.get("outline", [])[:1]:
        x0, y0, x1, y1 = bbox(o)
        cl = [(pts, abs(pts[0][0] - pts[-1][0]) < 0.01) for k, pts, _ in root["items"] if k == "clear"]
        cxs = [pts[0][0] for pts, vert in cl if vert]
        cys = [pts[0][1] for pts, vert in cl if not vert]
        allpts = [p for d in (root,) + tuple(layers) for k, ps, _ in d["items"] if k in ("poly", "clear")
                  for p in ps] + o
        ex0, ey0, ex1, ey1 = bbox(allpts)
        off = 0.045 * max(x1 - x0, y1 - y0)
        xs = sorted({round(v, 2) for v in [x0, x1] + ([min(cxs), max(cxs)] if cxs else [])})
        ys = sorted({round(v, 2) for v in [y0, y1] + ([min(cys), max(cys)] if cys else [])})
        # rails: centre lines of separating rails / mullions (8070, 8060, facade sticks) in root and layers
        hr, vr = set(), set()
        for d in (root,) + tuple(layers):
            for k, ps, st in d["items"]:
                pc = st.get("piece") if k == "poly" else None
                if pc is None or pc.get("Type") not in ("8070", "8060", "8340", "8350", "8320", "8330"):
                    continue
                bx0, by0, bx1, by1 = bbox(ps)
                if bx1 - bx0 >= by1 - by0:
                    hr.add(round((by0 + by1) / 2, 1))
                else:
                    vr.add(round((bx0 + bx1) / 2, 1))
        yb = ey0 - off
        for a, b in zip(xs, xs[1:]):
            _dim(ax, a, b, yb, True)
        if len(xs) > 2:
            _dim(ax, xs[0], xs[-1], yb - off * 0.8, True)
        vis_right, vis_left = (ex0 - off, ex1 + off) if mirror else (ex1 + off, ex0 - off)
        for a, b in zip(ys, ys[1:]):
            _dim(ax, a, b, vis_right, False)
        if len(ys) > 2:
            _dim(ax, ys[0], ys[-1], vis_right + (off * 0.8 if not mirror else -off * 0.8), False)
        if hr:
            pts = sorted({y0, y1} | {v for v in hr if y0 < v < y1})
            for a, b in zip(pts, pts[1:]):
                _dim(ax, a, b, vis_left, False)
        if vr:
            pts = sorted({x0, x1} | {v for v in vr if x0 < v < x1})
            for a, b in zip(pts, pts[1:]):
                _dim(ax, a, b, ey1 + off, True)


def piece_labels(ax, trees, max_pieces=45):
    """FP-style labels: '<DXF folder> - <code>' along each profile, glass type in its cell (skipped when crowded)."""
    polys = [(ps, st["piece"]) for d in trees for k, ps, st in d["items"] if k == "poly" and st.get("piece") is not None]
    if len(polys) > max_pieces:
        return
    for ps, pc in polys:
        dxf = (pc.get("DXF") or "").rsplit(".", 1)[0].replace("\\", " - ")
        if not dxf or pc.get("ElementGhost") == "1":
            continue
        bx0, by0, bx1, by1 = bbox(ps)
        vert = (by1 - by0) > (bx1 - bx0)
        ax.text((bx0 + bx1) / 2, (by0 + by1) / 2, dxf, fontsize=4.5, ha="center", va="center",
                rotation=90 if vert else 0, color="#222", zorder=35, clip_on=True)
    for d in trees:
        for r, n in zip(d.get("glass_rects", []), d.get("glass_nodes", [])):
            g = next((x for x in n.findall("FP_PIECE") if x.get("Type") == "8510"), None)
            if g is None:
                continue
            bx0, by0, bx1, by1 = bbox(r)
            ax.text((bx0 + bx1) / 2, (by0 + by1) / 2, (g.get("DXF") or "").rsplit(".", 1)[0].replace("\\", " - "),
                    fontsize=5.5, ha="center", va="center", color="#334", zorder=35, clip_on=True)


def view_fp(ax, root, containers):
    """FP convention: every layer container (one per bay) gets its own slanted cut inside its own outline;
    front layer (1) below, the next layer back above. n layers -> n-1 parallel cuts (our generalisation, unverified).
    Cut direction (one module only): the 1st container's cut rises left to right, the 2nd falls -> we alternate."""
    paint(ax, root)
    for ci, layers in enumerate(containers):
        pts = [p for d in layers for o in d["outline"] for p in o]
        if not pts:
            continue
        x0, y0, x1, y1 = bbox(pts)
        H = y1 - y0
        n = len(layers)
        bases = [0.55] if n == 2 else [0.15 + 0.6 * k / (n - 1) for k in range(n - 1)] if n > 2 else []
        cuts = [(y0 + H * b, y0 + H * (b + 0.2)) if ci % 2 == 0 else (y0 + H * (b + 0.2), y0 + H * b) for b in bases]
        prev = (y0, y0)
        for d, c in zip(layers, cuts + [(y1, y1)]):
            band = Polygon([(x0, prev[0]), (x1, prev[1]), (x1, c[1]), (x0, c[0])], transform=ax.transData)
            prev = c
            paint(ax, d, clip=band, z=10, opaque=True)
        for c in cuts:
            ax.plot([x0, x1], list(c), color="#000", lw=0.8, zorder=16)


def glass_cells(trees, ref):
    """Turn each tree's glass insert points into visible openings: from the point, the nearest piece outline to the
    left/right/below/above, or the reference outline. trees[0] is the root; a layer's glass is bounded by the root's
    pieces and its own layer's pieces only. Axis-aligned openings only (shaped ones not handled)."""
    def box_of(d):
        return [bbox(pts) for k, pts, _ in d["items"] if k == "poly"]

    root_boxes = box_of(trees[0])
    rx0, ry0, rx1, ry1 = bbox(ref) if ref else (-1e9, -1e9, 1e9, 1e9)
    for i, d in enumerate(trees):
        boxes = root_boxes + (box_of(d) if i else [])
        d["glass_rects"] = []
        for ix, iy in d.get("glass_ins", []):
            left = max([b[2] for b in boxes if b[1] < iy < b[3] and b[2] <= ix] + [rx0])
            right = min([b[0] for b in boxes if b[1] < iy < b[3] and b[0] >= ix] + [rx1])
            lo = max([b[3] for b in boxes if b[0] < ix < b[2] and b[3] <= iy] + [ry0])
            hi = min([b[1] for b in boxes if b[0] < ix < b[2] and b[1] >= iy] + [ry1])
            d["glass_rects"].append([(left, lo), (right, lo), (right, hi), (left, hi)])


def containers_of(t):
    """Layer containers (ElementType 1142, one per bay) -> list of their FP_TREE_LAYERn elements, in layer order."""
    return [[c for c in n if c.tag in LAYER_TAGS] for n in t.iter("FP_NODE") if n.get("ElementType") == "1142"]


def prm_dirs(prmdir, sight):
    """FP keeps sight-specific opening symbols in Prm subfolders: an external-sight drawing uses
    Prm/OPEN_EXT/<name>.PRM, falling back to Prm/<name>.PRM. (Prm/PRM_INT_INVERTED holds push/dashed variants,
    apparently for the opposite view; not used.)"""
    if not prmdir:
        return None
    prmdir = str(prmdir)
    return [os.path.join(prmdir, "OPEN_EXT"), prmdir] if sight == "ext" else [prmdir]


def render(ax, text: str, prmdir, sight: str | None = None):
    """Draw FP's cutaway view of one style into ax (with dimensions; mirrored when `sight` differs from the side
    the style was drawn for). `sight` None = as stored. Returns (log, mirror, size) where size = (W, H) of the
    reference outline in model units, or None."""
    _, t = parse_text(text)
    side = style_side(text)
    sight = sight or side
    mirror = sight != side
    prmdir = prm_dirs(prmdir, sight)
    log: list[str] = []
    rootd = collect(t, prmdir, log, "root", mirror)
    conts = [[collect(lt, prmdir, log, f"bay{ci + 1}.{lt.tag[-6:]}", mirror) for lt in c]
             for ci, c in enumerate(containers_of(t))]
    layers_flat = [d for c in conts for d in c]
    glass_cells([rootd] + layers_flat, rootd["outline"][0] if rootd["outline"] else None)
    rootd["outline"] = rootd["outline"][:1]
    view_fp(ax, rootd, conts)
    outline_ref(ax, rootd, mirror, layers_flat)
    piece_labels(ax, [rootd] + layers_flat)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.autoscale_view()
    if mirror:
        ax.invert_xaxis()
    size = None
    if rootd["outline"]:
        x0, y0, x1, y1 = bbox(rootd["outline"][0])
        size = (x1 - x0, y1 - y0)
    return log, mirror, size
