"""PDF output of `fpptools str sheet`: one Letter-landscape page per style (plus continuation pages).

Design language from customReports docs/10 (red top rule, DARK/COOL text, pastel fills in the elevation).
Fonts: titles use Barlow (a DIN-style face, SIL OFL, bundled in render/fonts with its licence), else Bahnschrift /
Calibri from Windows, else DejaVu Sans; body text uses Calibri from Windows (never shipped), else DejaVu Sans.
Every .ttf/.otf in the folder named by $FPPTOOLS_FONTS is registered too.
"""

from __future__ import annotations

import os
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

from matplotlib import font_manager, rc_context
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

from fpptools.render import elevation
from fpptools.sheet_data import NODE_NAMES, USE_NAMES, SheetData

RED = "#E90018"
DARK = "#222222"
COOL = "#4C4D53"
GREY = "#A6ACB0"
BAND = "#F2F3F4"

PAGE_W, PAGE_H = 11.0, 8.5
FS = 6.4                      # table font size (pt)
ROW = 1.45 * FS               # row height (pt)
ENV_FONTS = "FPPTOOLS_FONTS"
CAP_KIT_ROWS, CAP_FIX_ROWS, CAP_ROWS, CAP_MACH_ROWS = 7, 24, 8, 22   # '... N more' beyond these

LABELS = {
    "en": {
        "config": "Configuration", "size": "Size", "folder": "Folder", "unique": "Unique code",
        "description": "Description", "drawn": "Drawn for {side}, seen from {view}",
        "ext": "outside", "int": "inside", "cont": "(continued)",
        "s1": "1. Profiles", "s2": "2. Kits", "s3": "3. Joinery", "s4": "4. Pane tables", "s5": "5. Machinings",
        "use": "Use", "series": "Series", "code": "Code", "qty": "Qty", "desc": "Description",
        "opt": "Opt.", "conf": "Conf.", "mult": "x", "type": "Type", "openings": "Openings", "glass": "Glass",
        "beads": "Beads", "panetable": "Pane table", "pa": "Profile A", "pb": "Profile B", "fittings": "Fittings",
        "node": "node", "style": "Style",
        "n_profiles_db": "Descriptions, compounds and components: database not read (--no-db).",
        "n_kit_flags": "Opt./Conf. are FP's raw 0/1 flags (Confirmed is not documented).",
        "n_kit_db": "Kit contents, choices and size rules: database not read (--no-db).",
        "no_kits": "No kits in this style.",
        "joint_none": "{n} NOD joint record(s) between this style's profiles carry no fitting.",
        "joint_unres": "Multijoint fittings: not resolved (NOD folder not found or unreadable).",
        "glazing": "Glazing fittings (in the style)", "joints": "Multijoint fittings (NOD)",
        "n_fix_db": "Profile fixings: database not read (--no-db).",
        "no_profiles": "No profiles found in this style.",
        "n_pane_db": "Glass and beads as in the style; pane tables: database not read (--no-db).",
        "n_mach_db": "Machinings: database not read (--no-db).",
        "no_panes": "No glazed openings found in this style.",
        "prm_missing": "Opening symbol not found (PRM): {names}.",
        "prm_dir": "PRM folder not found: opening symbols are not drawn.",
        "draw_err": "Elevation not drawn: {err}",
        "unres": "not resolved: {why}", "unres_short": "not resolved", "compound": "compound", "main": "main",
        "kit_nf": "kit not found in the database", "collection": "Collection",
        "kind": {"machining": "machining", "warning": "warning", "error": "error", "fictitious": "fictitious",
                 "profile": "profile", "glass": "glass", "panel": "panel"},
        "dim": {"H": "H", "O1": "sash W"}, "no_default": "none", "choices": "{name}: {n} options, default: {default}",
        "limits": "Limits", "via": "via", "fkind": {"fitting": "fitting", "profile": "profile"}, "profile": "Profile",
        "cut": "Cut", "fixings": "Profile fixings", "no_fixings": "No profile fixings in the database.",
        "pt_nf": "pane table {code} not found", "pt_none": "no pane table in the style", "tol": "tolerance",
        "rooms_unres": "Glazing room not resolved: tables that could apply are not listed.",
        "could_apply": "Pane tables that could apply", "combos": "Combos", "no_others": "No other pane table applies.",
        "no_mach": "No machining rows for the profiles of this style.", "unknown": "unknown", "in_kit": "in kit {kits}",
        "not_in_kit": "not in any kit of this style", "off": "off", "machine": "Machine", "ldt": "LDT files",
        "fitting": "Fitting", "kit": "Kit", "partner_note": "Grey rows also involve a profile that is not in this style.",
        "compat": "LDTs registered per profile", "base_profile": "Base profile", "thick": "Thick.", "room": "Room",
        "no_combos": "No combinations for the glazing room.", "more": "… {n} more",
    },
    "es": {
        "config": "Configuración", "size": "Tamaño", "folder": "Carpeta", "unique": "Nombre único",
        "description": "Descripción", "drawn": "Dibujada para {side}, vista desde {view}",
        "ext": "el exterior", "int": "el interior", "cont": "(continuación)",
        "s1": "1. Perfiles", "s2": "2. Kits", "s3": "3. Uniones", "s4": "4. Tablas de paneles",
        "s5": "5. Mecanizados",
        "use": "Uso", "series": "Serie", "code": "Código", "qty": "Cant.", "desc": "Descripción",
        "opt": "Opc.", "conf": "Conf.", "mult": "x", "type": "Tipo", "openings": "Huecos", "glass": "Vidrio",
        "beads": "Junquillos", "panetable": "Tabla de panel", "pa": "Perfil A", "pb": "Perfil B",
        "fittings": "Accesorios", "node": "nodo", "style": "Estructura",
        "n_profiles_db": "Descripciones, compuestos y componentes: base de datos no leída (--no-db).",
        "n_kit_flags": "Opc./Conf. son los indicadores 0/1 originales de FP (Confirmado no está documentado).",
        "n_kit_db": "Contenido de los kits, opciones y reglas de medidas: base de datos no leída (--no-db).",
        "no_kits": "Esta estructura no tiene kits.",
        "joint_none": "{n} unión(es) NOD entre los perfiles de esta estructura no llevan accesorio.",
        "joint_unres": "Accesorios de multiunión: no resuelto (carpeta NOD no encontrada o ilegible).",
        "glazing": "Accesorios de acristalamiento (en la estructura)", "joints": "Accesorios de multiunión (NOD)",
        "n_fix_db": "Fijaciones de perfiles: base de datos no leída (--no-db).",
        "no_profiles": "No se encontraron perfiles en esta estructura.",
        "n_pane_db": "Vidrio y junquillos como en la estructura; tablas de paneles: base de datos no leída (--no-db).",
        "n_mach_db": "Mecanizados: base de datos no leída (--no-db).",
        "no_panes": "No se encontraron huecos acristalados en esta estructura.",
        "prm_missing": "Símbolo de apertura no encontrado (PRM): {names}.",
        "prm_dir": "Carpeta PRM no encontrada: no se dibujan los símbolos de apertura.",
        "draw_err": "Alzado no dibujado: {err}",
        "unres": "no resuelto: {why}", "unres_short": "no resuelto", "compound": "compuesto", "main": "principal",
        "kit_nf": "kit no encontrado en la base de datos", "collection": "Colección",
        "kind": {"machining": "mecanizado", "warning": "aviso", "error": "error", "fictitious": "ficticio",
                 "profile": "perfil", "glass": "vidrio", "panel": "panel"},
        "dim": {"H": "H", "O1": "ancho hoja"}, "no_default": "ninguna",
        "choices": "{name}: {n} opciones, por defecto: {default}",
        "limits": "Límites", "via": "vía", "fkind": {"fitting": "accesorio", "profile": "perfil"},
        "profile": "Perfil", "cut": "Corte", "fixings": "Fijaciones de perfiles",
        "no_fixings": "Sin fijaciones de perfiles en la base de datos.",
        "pt_nf": "tabla de panel {code} no encontrada", "pt_none": "sin tabla de panel en la estructura",
        "tol": "tolerancia", "rooms_unres": "Espacio útil no resuelto: no se listan las tablas aplicables.",
        "could_apply": "Tablas de panel aplicables", "combos": "Comb.", "no_others": "No aplica otra tabla de panel.",
        "no_mach": "Sin mecanizados para los perfiles de esta estructura.", "unknown": "desconocido",
        "in_kit": "en kit {kits}", "not_in_kit": "en ningún kit de esta estructura", "off": "desact.",
        "machine": "Máquina", "ldt": "Archivos LDT", "fitting": "Accesorio", "kit": "Kit",
        "partner_note": "Las filas grises incluyen un perfil que no está en esta estructura.",
        "compat": "LDT registrados por perfil", "base_profile": "Perfil base", "thick": "Esp.", "room": "Espacio",
        "no_combos": "Sin combinaciones para el espacio útil.", "more": "… {n} más",
    },
}


# -- fonts ----------------------------------------------------------------------

BUNDLED_FONTS = Path(__file__).parent / "fonts"   # Barlow (SIL OFL, OFL.txt alongside)


def _register_fonts() -> None:
    for d in (BUNDLED_FONTS, os.environ.get(ENV_FONTS)):
        if d and os.path.isdir(d):
            for f in sorted(Path(d).iterdir()):
                if f.suffix.lower() in (".ttf", ".otf"):
                    try:
                        font_manager.fontManager.addfont(str(f))
                    except Exception:  # a broken font file must not stop the report
                        pass


def font_families() -> tuple[list[str], list[str]]:
    """(title family list, body family list): only families that exist, DejaVu Sans as the last resort."""
    _register_fonts()
    have = {f.name for f in font_manager.fontManager.ttflist}
    title = [n for n in ("Barlow", "DIN Pro", "DINPro", "Bahnschrift", "Calibri") if n in have][:1] + ["DejaVu Sans"]
    body = [n for n in ("Calibri",) if n in have] + ["DejaVu Sans"]
    return title, body


# -- block layout -----------------------------------------------------------------

@dataclass
class Line:
    kind: str                       # section | sub | header | row | note
    cells: list[str] = field(default_factory=list)
    cols: list[tuple[float, str]] = field(default_factory=list)   # (width fraction, 'l'|'r')
    keep: bool = False              # keep together with the next line
    text: str = ""
    muted: bool = False             # secondary text (COOL)

    @property
    def height(self) -> float:      # points
        return {"section": 1.9, "sub": 1.25, "header": 1.2, "row": 1.0, "note": 1.0}[self.kind] * ROW


def _trunc(s: str, width_pt: float) -> str:
    n = max(int(width_pt / (FS * 0.50)), 3)
    return s if len(s) <= n else s[:n - 1] + "…"


def _wrap(text: str, width_pt: float) -> list[str]:
    n = max(int(width_pt / (FS * 0.47)), 12)
    return textwrap.wrap(text, n) or [""]


def _short_guid(s: str) -> str:
    return s if len(s) <= 12 else s[:8] + "…"


def _g(v) -> str:
    """number for a table cell: no trailing zeros, empty for None."""
    if v is None:
        return ""
    return f"{round(float(v), 2):g}"


def _more(n: int, L: dict) -> str:
    return L["more"].format(n=n)


def build_lines(d: SheetData, L: dict) -> list[Line]:
    out: list[Line] = []
    db = d.db

    def section(title):
        out.append(Line("section", text=title, keep=True))

    def table(cols, header, rows, muted=()):
        out.append(Line("header", cells=header, cols=cols, keep=bool(rows)))
        for i, r in enumerate(rows):
            out.append(Line("row", cells=r, cols=cols, keep=i == 0 and len(rows) > 1, muted=i in muted))

    def note(text):
        out.append(Line("note", text=text))

    def text_row(text, muted=False):
        out.append(Line("row", cells=[text], cols=[(1.0, "l")], muted=muted))

    def part(attr: str, nodb_key: str):
        """(section object, None) when available, else (None, message to print). Never guessed."""
        if db is None:
            return None, L[nodb_key]
        if db.error:
            return None, L["unres"].format(why=db.error)
        obj = getattr(db, attr)
        if obj is None:
            return None, L["unres"].format(why="-")
        return obj, None

    # 1. profiles
    section(L["s1"])
    profs, msg = part("profiles", "n_profiles_db")
    if d.profiles:
        if profs is None:
            table([(.32, "l"), (.24, "l"), (.34, "l"), (.10, "r")], [L["use"], L["series"], L["code"], L["qty"]],
                  [[USE_NAMES.get(p.use, f"Use {p.use}"), p.series, p.code, str(p.qty)] for p in d.profiles])
        else:
            cols = [(.22, "l"), (.13, "l"), (.21, "l"), (.35, "l"), (.09, "r")]
            rows = []
            for p in d.profiles:
                pd = profs.get(p.series, p.code)
                desc = (pd.description if pd and pd.found else L["unres_short"])
                if pd and pd.found and pd.compound:
                    desc += f" ({L['compound']})"
                rows.append([USE_NAMES.get(p.use, f"Use {p.use}"), p.series, p.code, desc, str(p.qty)])
                if pd and pd.compound:
                    for k, c in enumerate(pd.components, 1):
                        rows.append(["", f".{k}", f"{c.series}\\{c.code}" if c.series else c.code,
                                     c.description + (f" ({L['main']})" if c.master else ""), f"x{c.count}"])
            table(cols, [L["use"], L["series"], L["code"], L["desc"], L["qty"]], rows)
    else:
        note(L["no_profiles"])
    if profs is None:
        note(msg)
    for n in (profs.notes if profs else []):
        note(L["unres"].format(why=n))

    # 2. kits
    section(L["s2"])
    kits_db, msg = part("kits", "n_kit_db")
    if d.kits:
        cols = [(.27, "l"), (.47, "l"), (.08, "r"), (.08, "r"), (.10, "r")]
        det = [(.28, "l"), (.38, "l"), (.08, "r"), (.07, "l"), (.19, "l")]
        for g in d.kits:
            name = NODE_NAMES.get(g.node_type, f"Node {g.node_type}") if g.node_type else L["style"]
            title = f"{name} ({L['node']} {g.node_code})" if g.node_type else name
            out.append(Line("sub", text=title, keep=True))
            out.append(Line("header", cells=[L["code"], L["desc"], L["opt"], L["conf"], L["mult"]], cols=cols,
                            keep=True))
            def collection_of(k):
                kd_ = kits_db.kits.get(k.code) if kits_db else None
                return (kd_.collection or "") if kd_ and kd_.found else ""

            # kits without a collection first, then one block per collection (alphabetical, stable inside)
            ordered = sorted(g.kits, key=lambda k: (collection_of(k) != "", collection_of(k).casefold()))
            current = ""
            for k in ordered:
                kd = kits_db.kits.get(k.code) if kits_db else None
                coll = collection_of(k)
                if coll != current:
                    current = coll
                    if coll:
                        text_row(f"{L['collection']}: {coll}", muted=True)
                desc = kd.description if kd and kd.found and kd.description else k.description
                out.append(Line("row", cells=[k.code, desc, "1" if k.optional else "0", "1" if k.confirmed else "0",
                                              k.multiply], cols=cols))
                if kits_db is None:
                    continue
                if kd is None or not kd.found:
                    text_row("   " + L["unres"].format(why=(kd.note if kd and kd.note else L["kit_nf"])), muted=True)
                    continue
                rows = []
                for r in kd.fixed:
                    finals = r.replaced_by or [r]
                    for f in finals:
                        kind = f.kind
                        label = f" [{L['kind'].get(kind, kind)}]" if kind not in ("hardware", "unknown") else ""
                        fdesc = (f.description or "") if (r.found or r.replaced_by) else L["unres_short"]
                        hand = r.hand if f is r else ""
                        rules = "; ".join(f"{L['dim'].get(s.label, s.label)} {_g(s.lo)}-{_g(s.hi)}"
                                          for s in r.rules) if f is r else ""
                        if f is r and r.more_ranges:
                            rules += " +"
                        rows.append(["   " + f.code, fdesc + label, _g(f.qty), hand, rules])
                for cells in rows[:CAP_KIT_ROWS]:
                    out.append(Line("row", cells=cells, cols=det))
                if len(rows) > CAP_KIT_ROWS:
                    text_row("   " + _more(len(rows) - CAP_KIT_ROWS, L), muted=True)
                for cg in kd.choices:
                    defs = ", ".join(f"{x.code} x{_g(x.qty)}" for x in cg.default) or L["no_default"]
                    text_row("   " + L["choices"].format(name=cg.name or f"#{cg.group_id}", n=len(cg.rows),
                                                          default=defs), muted=True)
                if kd.limits:
                    text_row("   " + L["limits"] + ": " + "; ".join(f"{a} {_g(b)}" for a, b in kd.limits.items()),
                             muted=True)
        note(L["n_kit_flags"])
    else:
        note(L["no_kits"])
    if kits_db is None:
        note(msg)
    for n in (kits_db.notes if kits_db else []):
        note(L["unres"].format(why=n))

    # 3. joinery
    section(L["s3"])
    if not d.nod_checked:
        note(L["joint_unres"])
    else:
        if d.joints:
            out.append(Line("sub", text=L["joints"], keep=True))
            table([(.30, "l"), (.30, "l"), (.40, "l")], [L["pa"], L["pb"], L["fittings"]],
                  [[j.profile_a, j.profile_b, "; ".join(f"{c} {t}".strip() + f" x{q}" for c, t, q in j.fittings)]
                   for j in d.joints])
        note(L["joint_none"].format(n=d.joints_without_fittings))
    if d.glazing_fittings:
        out.append(Line("sub", text=L["glazing"], keep=True))
        table([(.14, "l"), (.46, "l"), (.08, "r"), (.08, "r"), (.24, "l")],
              [L["code"], L["desc"], L["type"], L["mult"], L["openings"]],
              [[g.code, g.description, g.type, g.multiply, " ".join(g.openings)] for g in d.glazing_fittings])
    if profs is None:
        note(L["n_fix_db"] if db is None else msg)
    else:
        rows = []
        for p in d.profiles:
            pd = profs.get(p.series, p.code)
            if pd is None or not pd.found:
                rows.append([p.code, "", L["unres_short"], "", "", ""])
                continue
            if not pd.fixings:
                if pd.fixings_note:
                    rows.append([p.code, "", pd.fixings_note, "", "", ""])
                continue
            for k, f in enumerate(pd.fixings):
                who = p.code if k == 0 else ""
                if k == 0 and f.from_profile:
                    who += f" ({L['via']} {f.from_profile})"
                code = f.code or L["unres_short"]
                if f.series and f.code:
                    code = f"{f.series}\\{f.code}" if f.kind == "profile" else f.code
                rows.append([who, L["fkind"].get(f.kind, f.kind), code, f.description,
                             _g(f.qty) + ("*" if f.optional else ""), _g(f.cut_length) if f.cut_length else ""])
        if rows:
            out.append(Line("sub", text=L["fixings"], keep=True))
            table([(.20, "l"), (.08, "l"), (.22, "l"), (.34, "l"), (.08, "r"), (.08, "r")],
                  [L["profile"], L["type"], L["code"], L["desc"], L["qty"], L["cut"]], rows[:CAP_FIX_ROWS])
            if len(rows) > CAP_FIX_ROWS:
                note(_more(len(rows) - CAP_FIX_ROWS, L))
        else:
            note(L["no_fixings"])

    # 4. pane tables
    section(L["s4"])
    panes_db, msg = part("panes", "n_pane_db")
    if panes_db is None:
        if d.panes:
            table([(.16, "l"), (.18, "l"), (.40, "l"), (.26, "l")],
                  [L["openings"], L["glass"], L["beads"], L["panetable"]],
                  [[" ".join(p.openings), p.glass, p.beads, _short_guid(p.pane_table)] for p in d.panes])
        else:
            note(L["no_panes"])
        note(msg)
    else:
        if not panes_db.openings:
            note(L["no_panes"])
        else:
            table([(.16, "l"), (.18, "l"), (.66, "l")], [L["openings"], L["glass"], L["beads"]],
                  [[" ".join(o.openings), o.glass, o.beads] for o in panes_db.openings])
        shown = set()
        for o in panes_db.openings:
            if o.table is None:
                why = (L["pt_nf"].format(code=_short_guid(o.pane_table_code)) if o.pane_table_code
                       else L["pt_none"])
                text_row(f"{' '.join(o.openings)}: " + L["unres"].format(why=why), muted=True)
                continue
            t = o.table
            if t.code in shown:
                continue
            shown.add(t.code)
            out.append(Line("sub", text=f"{t.name or _short_guid(t.code)}   ({L['tol']} {_g(t.tolerance)})",
                            keep=True))
            _combos(out, t, L)
        if "rooms_not_resolved" in panes_db.notes:
            note(L["rooms_unres"])
        for n in panes_db.notes:
            if n != "rooms_not_resolved" and "not found" not in n:
                note(L["unres"].format(why=n))
        others = [t for t in panes_db.could_apply if t.code not in shown]
        if others:
            out.append(Line("sub", text=L["could_apply"], keep=True))
            table([(.46, "l"), (.30, "l"), (.12, "r"), (.12, "r")],
                  [L["panetable"], L["series"], L["combos"], L["tol"]],
                  [[t.name or _short_guid(t.code), ", ".join(t.series), str(len(t.combos)), _g(t.tolerance)]
                   for t in others[:CAP_ROWS]])
            if len(others) > CAP_ROWS:
                note(_more(len(others) - CAP_ROWS, L))
        elif panes_db.rooms_resolved:
            note(L["no_others"])

    # 5. machinings
    section(L["s5"])
    mach, msg = part("machinings", "n_mach_db")
    if mach is None:
        note(msg)
    elif not mach.resolved:
        note(L["unres"].format(why=mach.note or "-"))
    else:
        if not mach.machinings:
            note(L["no_mach"])
        else:
            rows, muted = [], set()
            for m in mach.machinings[:CAP_MACH_ROWS]:
                if m.in_style_kits is None:
                    kit = L["unknown"]
                elif m.in_style_kits:
                    kit = L["in_kit"].format(kits=", ".join(m.kits[:2]) + (" …" if len(m.kits) > 2 else "")
                                             if m.kits else "?")
                else:
                    kit = L["not_in_kit"]
                fit = (m.fitting or "-") + (f" ({L['off']})" if m.disabled else "")
                rows.append([m.machine, m.kind or (str(m.kind_code) if m.kind_code is not None else ""),
                             ", ".join(m.ldts), fit, kit])
                if m.profiles_not_in_style:
                    muted.add(len(rows) - 1)
            table([(.14, "l"), (.07, "l"), (.28, "l"), (.17, "l"), (.34, "l")],
                  [L["machine"], L["type"], L["ldt"], L["fitting"], L["kit"]], rows, muted=muted)
            if len(mach.machinings) > CAP_MACH_ROWS:
                note(_more(len(mach.machinings) - CAP_MACH_ROWS, L))
            if muted:
                note(L["partner_note"])
        if mach.compat:
            out.append(Line("sub", text=L["compat"], keep=True))
            table([(.15, "l"), (.31, "l"), (.27, "l"), (.27, "l")],
                  [L["machine"], L["ldt"], L["profile"], L["base_profile"]],
                  [[c.machine, c.ldt, c.profile, c.base_profile] for c in mach.compat[:CAP_ROWS]])
            if len(mach.compat) > CAP_ROWS:
                note(_more(len(mach.compat) - CAP_ROWS, L))
    return out


def _combos(out: list[Line], t, L: dict) -> None:
    rows = []
    for c in t.combos[:CAP_ROWS]:
        beads = " + ".join(b.rsplit("\\", 1)[-1] for b in c.beads) or "-"
        fits = "; ".join(f"{f.code} x{_g(f.qty)}" for f in c.fittings[:4]) + (" …" if len(c.fittings) > 4 else "")
        rows.append([_g(c.thickness), _g(c.room), beads, fits])
    if rows:
        cols = [(.10, "r"), (.10, "r"), (.36, "l"), (.44, "l")]
        out.append(Line("header", cells=[L["thick"], L["room"], L["beads"], L["fittings"]], cols=cols, keep=True))
        for i, r in enumerate(rows):
            out.append(Line("row", cells=r, cols=cols, keep=i == 0 and len(rows) > 1))
        if len(t.combos) > CAP_ROWS:
            out.append(Line("note", text=L["more"].format(n=len(t.combos) - CAP_ROWS)))
    else:
        out.append(Line("note", text=L["no_combos"]))


def _height(ln: Line, width_pt: float) -> float:
    """Line height in a column of this width (notes wrap)."""
    if ln.kind == "note":
        return ln.height + (len(_wrap(ln.text, width_pt)) - 1) * ROW
    return ln.height


def paginate(lines: list[Line], first_pt: float, col_pt: float, first_w_pt: float, col_w_pt: float,
             cont_cols: int = 2) -> list[list[list[Line]]]:
    """Split lines into pages of columns: page 1 has one column (beside the elevation), every continuation page
    has `cont_cols` columns filled one after the other. A run of `keep` lines plus the line after it is never
    split. Returns pages -> columns -> lines."""
    pages: list[list[list[Line]]] = [[[]]]
    room, width = first_pt, first_w_pt

    def next_slot():
        nonlocal room, width
        if len(pages) > 1 and len(pages[-1]) < cont_cols:
            pages[-1].append([])
        else:
            pages.append([[]])
        room, width = col_pt, col_w_pt

    i = 0
    while i < len(lines):
        if lines[i].kind == "section" and pages[-1][-1]:
            # a section that fits in one column starts a new column rather than being split across two
            end = next((k for k in range(i + 1, len(lines)) if lines[k].kind == "section"), len(lines))
            need = sum(_height(x, width) for x in lines[i:end])
            if room < need <= col_pt:
                next_slot()
        j = i
        while j < len(lines) - 1 and lines[j].keep:
            j += 1
        run = lines[i:j + 1]
        if sum(_height(x, width) for x in run) > room and pages[-1][-1]:
            next_slot()
        for x in run:
            if _height(x, width) > room and pages[-1][-1]:
                next_slot()
            pages[-1][-1].append(x)
            room -= _height(x, width)
        i = j + 1
    return pages


# -- drawing ----------------------------------------------------------------------

def _pt_y(pt: float) -> float:
    return pt / 72 / PAGE_H


def _draw_lines(fig, lines: list[Line], x0: float, width: float, y_top: float, title_f, body_f) -> None:
    w_in = width * PAGE_W
    y = y_top
    for ln in lines:
        h = _pt_y(ln.height)
        if ln.kind == "section":
            y -= _pt_y(0.5 * ROW)
            fig.text(x0, y, ln.text, fontsize=FS + 3.2, family=title_f, fontweight="bold", color=DARK, va="top")
            y -= h - _pt_y(0.5 * ROW)
            continue
        if ln.kind == "sub":
            fig.text(x0, y, ln.text, fontsize=FS + 0.4, family=body_f, fontweight="bold", color=DARK, va="top")
        elif ln.kind == "note":
            wrapped = _wrap(ln.text, w_in * 72)
            for k, w in enumerate(wrapped):
                fig.text(x0, y - k * _pt_y(ROW), w, fontsize=FS - 0.2, family=body_f, style="italic", color=COOL,
                         va="top")
            y -= _pt_y(ROW) * (len(wrapped) - 1)
        else:
            x = x0
            prev_al = "l"
            for (frac, al), cell in zip(ln.cols, ln.cells):
                cw = frac * w_in * 72
                txt = _trunc(cell, cw - 6)
                pad = 0.012 * width if (al == "l" and prev_al == "r") else 0   # gap after a right-aligned column
                prev_al = al
                fig.text(x + pad + (frac * width if al == "r" else 0), y, txt, fontsize=FS, family=body_f,
                         fontweight="bold" if ln.kind == "header" else "normal",
                         color=COOL if ln.muted else DARK,
                         ha="right" if al == "r" else "left", va="top")
                x += frac * width
            if ln.kind == "header":
                fig.add_artist(Line2D([x0, x0 + width], [y - h * 0.98, y - h * 0.98], transform=fig.transFigure,
                                      color=GREY, lw=0.6))
        y -= h


def _furniture(fig, d: SheetData, L: dict, title_f, body_f, *, page: int, pages: int, continued: bool,
               config_name: str, date: str, version: str, view_side: str, size_txt: str) -> None:
    fig.add_artist(Rectangle((0, 0.986), 1, 0.014, transform=fig.transFigure, fc=RED, ec="none"))
    fig.add_artist(Rectangle((0.02, 0.885), 0.96, 0.088, transform=fig.transFigure, fc=BAND, ec=GREY, lw=0.5))
    fig.text(0.03, 0.953, d.name + (f"  {L['cont']}" if continued else ""), fontsize=17, family=title_f,
             fontweight="bold", color=DARK, va="top")
    sub = f"{L['folder']}: {d.folder or '.'}     {L['unique']}: {d.unique_code or '-'}"
    fig.text(0.03, 0.918, _trunc_chars(sub, 120), fontsize=8, family=body_f, color=DARK, va="top")
    fig.text(0.03, 0.9, f"{L['description']}: {_trunc_chars(d.description or '-', 110)}", fontsize=8,
             family=body_f, color=DARK, va="top")
    fig.text(0.97, 0.955, f"{L['config']}: {config_name or '-'}", fontsize=8, family=body_f, color=DARK,
             ha="right", va="top")
    fig.text(0.97, 0.935, date, fontsize=8, family=body_f, color=DARK, ha="right", va="top")
    fig.text(0.97, 0.915, f"{L['size']}: {size_txt}", fontsize=8, family=body_f, color=DARK, ha="right", va="top")
    fig.text(0.97, 0.897, view_side, fontsize=8, family=body_f, color=COOL, ha="right", va="top")
    fig.add_artist(Line2D([0.02, 0.98], [0.046, 0.046], transform=fig.transFigure, color=DARK, lw=0.8))
    fig.text(0.02, 0.025, f"fpptools {version}", fontsize=6.5, family=body_f, color=COOL, va="center")
    fig.text(0.98, 0.025, f"emmegisoft   ·   {page} / {pages}", fontsize=8, family=title_f, color=DARK,
             ha="right", va="center")


def _trunc_chars(s: str, n: int) -> str:
    return s if len(s) <= n else s[:n - 1] + "…"


def _fmt_size(size) -> str:
    if not size:
        return "-"
    f = lambda v: f"{v:.0f}" if abs(v - round(v)) < 0.05 else f"{v:.1f}"  # noqa: E731
    return f"{f(size[0])} x {f(size[1])}"


def write_pdf(items: list[tuple[SheetData, str]], out_path, *, prm_dir, sight: str | None, lang: str = "en",
              config_name: str = "", date: str = "", version: str = "") -> int:
    """One sheet per (SheetData, xml_text). Returns the number of pages written.
    Never fails because of one style: a drawing error is printed on that sheet."""
    L = LABELS.get(lang, LABELS["en"])
    title_f, body_f = font_families()
    prm_ok = bool(prm_dir) and os.path.isdir(str(prm_dir))

    # layout first (pure), so the footer knows the page count
    right_x, right_w = 0.575, 0.405
    cont_x, cont_w = (0.03, 0.515), 0.455      # continuation pages: two columns
    col_pt = (0.865 - 0.07) * PAGE_H * 72
    plans = []
    for d, _ in items:
        plans.append(paginate(build_lines(d, L), col_pt, col_pt, right_w * PAGE_W * 72, cont_w * PAGE_W * 72))
    total = sum(len(p) for p in plans)

    n = 0
    with PdfPages(str(out_path)) as pdf:
        for (d, text), pages in zip(items, plans):
            side = sight or d.side
            known_size = d.size
            for pi, columns in enumerate(pages):
                n += 1
                fig = Figure(figsize=(PAGE_W, PAGE_H))
                notes: list[str] = list(d.notes)
                size = known_size
                with rc_context({"font.family": body_f}):
                    if pi == 0:
                        ax = fig.add_axes([0.03, 0.09, 0.52, 0.76])
                        try:
                            log, _mirror, esize = elevation.render(ax, text, prm_dir if prm_ok else None, side)
                            size = known_size = size or esize
                            missing = sorted({x[len("missing PRM "):] for x in log if x.startswith("missing PRM ")})
                            if missing:
                                notes.append(L["prm_missing"].format(names=", ".join(missing)))
                        except Exception as exc:  # per-style: report on the sheet, keep going
                            ax.clear()
                            ax.axis("off")
                            notes.append(L["draw_err"].format(err=f"{type(exc).__name__}: {exc}"))
                        if not prm_ok:
                            notes.append(L["prm_dir"])
                    view = L["drawn"].format(side=L[d.side], view=L[side])
                    _furniture(fig, d, L, title_f, body_f, page=n, pages=total, continued=pi > 0,
                               config_name=config_name, date=date, version=version, view_side=view,
                               size_txt=_fmt_size(size))
                    if pi == 0:
                        for k, t in enumerate(notes):
                            fig.text(0.03, 0.07 - k * 0.014, _trunc_chars(t, 140), fontsize=6.4, family=body_f,
                                     style="italic", color=COOL, va="top")
                        _draw_lines(fig, columns[0], right_x, right_w, 0.865, title_f, body_f)
                    else:
                        for x0, lines in zip(cont_x, columns):
                            _draw_lines(fig, lines, x0, cont_w, 0.865, title_f, body_f)
                        if len(columns) > 1:   # thin separator between the two columns
                            fig.add_artist(Line2D([0.5, 0.5], [0.07, 0.865], transform=fig.transFigure,
                                                  color=GREY, lw=0.4))
                    pdf.savefig(fig)
    return n
