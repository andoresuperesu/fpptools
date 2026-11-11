"""Minimal interpreter for FP Pro PRM drawing scripts (opening symbols). Read-only; for rendering only.

Language notes: customReports docs/04_prm_language.md. Unknown statements are ignored; an expression that fails
evaluates to 0 (the symbol is then drawn partly, never an error).
"""

from __future__ import annotations

import math
import os
import re


class PRM:
    def __init__(self, dirs):
        self.dirs = dirs
        self.prims = []

    def find(self, name):
        for d in self.dirs:
            for sub in ("", "MODELS"):
                p = os.path.join(d, sub, name.upper() + ".PRM")
                if os.path.exists(p):
                    return p
        return None

    def parse(self, path):
        lines = []
        with open(path, encoding="latin-1") as fh:
            for raw in fh:
                line = raw.split(";")[0].strip()
                # FP tolerates 'END IF' (seen in DECOR-96B)
                line = re.sub(r"^END\s+(IF|REPEAT|WHILE|OPTIONS|VAR)\b", r"END\1", line, flags=re.I)
                if line:
                    lines.append(line)
        return lines

    def ev(self, expr, vars):
        e = expr.strip()
        # FP reads a dangling operator as 'op 0': -(ADIM[i]-) = -ADIM[i] (OPEN_EXT/LX-03, checked with prmvie32)
        e = re.sub(r"([-+*/])\s*(?=\)|$)", r"\1 0", e)
        e = re.sub(r"<>", "!=", e)
        e = re.sub(r"(?<![<>!=])=(?!=)", "==", e)
        e = re.sub(r"\bAND\b", " and ", e, flags=re.I)
        e = re.sub(r"\bOR\b", " or ", e, flags=re.I)
        e = re.sub(r"([A-Za-z_]\w*)\[([^\]]+)\]", r'__a("\1",\2)', e)

        def a(n, i):
            v = vars.get(n.upper(), {})
            return v.get(int(i), 0) if isinstance(v, dict) else v

        class D(dict):
            def __missing__(s, k):
                return 0

        env = D({k: v for k, v in vars.items() if not isinstance(v, dict)})
        env["__a"] = a
        env.update({"ISODD": lambda x: int(round(x)) % 2, "ISEVEN": lambda x: 1 - int(round(x)) % 2,
                    "sqrt": math.sqrt, "abs": abs,
                    "sin": lambda x: math.sin(math.radians(x)), "cos": lambda x: math.cos(math.radians(x))})
        try:
            return eval(e.upper().replace("__A(", "__a("), {"__builtins__": {}}, env)  # noqa: S307 (PRM files only)
        except Exception:
            return 0

    def setvar(self, lhs, val, vars):
        m = re.match(r"(\w+)\[(.+)\]", lhs.strip())
        if m:
            n = m.group(1).upper()
            i = int(self.ev(m.group(2), vars))
            if not isinstance(vars.get(n), dict):
                vars[n] = {}
            vars[n][i] = val
        else:
            vars[lhs.strip().upper()] = val

    def run(self, name, vars, ox=0, oy=0, depth=0):
        path = self.find(name)
        if not path or depth > 6:
            return
        lines = self.parse(path)
        body = []
        for line in lines:  # VAR defaults (only if not supplied)
            if line.upper().startswith("VAR "):
                lhs, rhs = line[4:].split("=", 1)
                n = re.match(r"(\w+)", lhs.strip()).group(1).upper()
                if n not in vars:
                    if "[" in lhs:
                        v = self.ev(rhs, vars)
                        vars[n] = {k: v for k in range(1, 21)}
                    else:
                        self.setvar(lhs, self.ev(rhs, vars), vars)
            elif line.upper() in ("ENDVAR", "ENDIFVAR"):
                pass
            else:
                body.append(line)
        self.st = {"x": ox, "y": oy, "lw": 1, "ls": 0}
        self.ox, self.oy = ox, oy
        self.exec(body, 0, len(body), vars, depth)

    def block_end(self, b, i, opens, closes, mids=()):
        d = 0
        j = i + 1
        mid = None
        while j < len(b):
            k = b[j].split()[0].upper()
            if k in opens:
                d += 1
            elif k in closes:
                if d == 0:
                    return j, mid
                d -= 1
            elif k in mids and d == 0 and mid is None:
                mid = j
            j += 1
        return j, mid

    def exec(self, b, i, end, vars, depth):
        st = self.st
        while i < end:
            line = b[i]
            k = line.split()[0].upper()
            arg = line[len(k):].strip()

            def args(arg=arg):
                return [self.ev(x, vars) for x in self.splitargs(arg)]

            if k == "SET":
                lhs, rhs = arg.split("=", 1)
                self.setvar(lhs, self.ev(rhs, vars), vars)
            elif re.match(r"^[A-Za-z_][\w\[\]]*\s*=", line) and not line.upper().startswith(("IF", "WHILE")):
                lhs, rhs = line.split("=", 1)  # FP accepts assignment without SET (seen in DECOR-96B)
                self.setvar(lhs, self.ev(rhs, vars), vars)
            elif k == "IF":
                j, mid = self.block_end(b, i, ("IF",), ("ENDIF",), ("ELSE",))
                if self.ev(arg, vars):
                    self.exec(b, i + 1, mid if mid else j, vars, depth)
                elif mid:
                    self.exec(b, mid + 1, j, vars, depth)
                i = j
            elif k == "WHILE":
                j, _ = self.block_end(b, i, ("WHILE",), ("ENDWHILE",))
                n = 0
                while self.ev(arg, vars) and n < 50:
                    self.exec(b, i + 1, j, vars, depth)
                    n += 1
                i = j
            elif k == "REPEAT":
                j, _ = self.block_end(b, i, ("REPEAT",), ("ENDREPEAT",))
                for _ in range(int(self.ev(arg, vars))):
                    self.exec(b, i + 1, j, vars, depth)
                i = j
            elif k == "OPTIONS":
                j, _ = self.block_end(b, i, ("OPTIONS",), ("ENDOPTIONS",))
                i = j
            elif k == "MOVETO":
                x, y = args()[:2]
                st["x"], st["y"] = self.ox + x, self.oy + y
            elif k == "MOVEREL":
                x, y = args()[:2]
                st["x"] += x
                st["y"] += y
            elif k in ("LINETO", "LINEREL"):
                x, y = args()[:2]
                nx, ny = (self.ox + x, self.oy + y) if k == "LINETO" else (st["x"] + x, st["y"] + y)
                self.prims.append(("line", [(st["x"], st["y"]), (nx, ny)], st["lw"], st["ls"]))
                st["x"], st["y"] = nx, ny
            elif k == "ARCTO":
                a = args()
                x, y, cx, cy = a[0] + self.ox, a[1] + self.oy, a[2] + self.ox, a[3] + self.oy
                d = a[4] if len(a) > 4 else 1
                a0 = math.atan2(st["y"] - cy, st["x"] - cx)
                a1 = math.atan2(y - cy, x - cx)
                r = math.hypot(st["x"] - cx, st["y"] - cy)
                if d > 0 and a1 < a0:
                    a1 += 2 * math.pi
                if d < 0 and a1 > a0:
                    a1 -= 2 * math.pi
                pts = [(cx + r * math.cos(a0 + (a1 - a0) * t / 16), cy + r * math.sin(a0 + (a1 - a0) * t / 16))
                       for t in range(17)]
                self.prims.append(("line", pts, st["lw"], st["ls"]))
                st["x"], st["y"] = x, y
            elif k in ("BOX", "RECTANGLE"):
                w, h = args()[:2]
                x, y = st["x"], st["y"]
                self.prims.append(("box" if k == "BOX" else "rect",
                                   [(x, y), (x + w, y), (x + w, y + h), (x, y + h)], st["lw"], st["ls"]))
            elif k in ("FCIRCLE", "CIRCLE"):
                r = args()[0]
                self.prims.append(("fcircle" if k == "FCIRCLE" else "circle", [(st["x"], st["y"])],
                                   max(r, st["lw"] / 2), st["ls"]))
            elif k == "DUPLICATE":
                a = args()
                c, dx, dy = int(a[1]), a[2], a[3]
                last = self.prims[-1] if self.prims else None
                if last:
                    for t in range(1, c + 1):
                        self.prims.append((last[0], [(px + dx * t, py + dy * t) for px, py in last[1]],
                                           last[2], last[3]))
            elif k == "LINEWIDTH":
                st["lw"] = args()[0]
            elif k == "LINESTYLE":
                st["ls"] = args()[0]
            elif k == "INSERT":
                save = dict(st)
                self.run(arg.split()[0], vars, self.ox, self.oy, depth + 1)
                self.st = st = save
            i += 1

    @staticmethod
    def splitargs(s):
        out = []
        d = 0
        cur = ""
        for ch in s:
            if ch in "([":
                d += 1
            if ch in ")]":
                d -= 1
            if ch == "," and d == 0:
                out.append(cur)
                cur = ""
            else:
                cur += ch
        if cur.strip():
            out.append(cur)
        return out
