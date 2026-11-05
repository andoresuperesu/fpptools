"""FP Pro design files (.STR structures, .BLK blocks, job records): find, read, write.

File facts (observed on FP Pro 11 configs):
- XML, encoding windows-1252, CRLF line endings; two XML declaration variants exist.
- Every STR has <FP_TREE NameStr="..." Description="SEE CDATA BELOW...">, also facades
  (<FP_FACADE> root with FP_TREE further down).
- NameStr is the "unique code" (FP Pro UI: "nombre unívoco").
- The description is Base64 (cp1252 text) inside <FP_DESCRIPTION DescrB64="..."><![CDATA[...]]>.
- The "name" shown in FP Pro's structure browser is the file name without extension.
"""

from __future__ import annotations

import base64
import binascii
import fnmatch
import os
import re
from dataclasses import dataclass
from pathlib import Path, PurePath

from lxml import etree

ENCODING = "cp1252"
EXTENSIONS = {"str": (".STR",), "blk": (".BLK",)}


# -- finding files --------------------------------------------------------------

def _norm(rel: str) -> str:
    return rel.replace("\\", "/").strip("/").casefold()


def find_files(root: Path, extensions: tuple[str, ...], under: str | None = None,
               match: str | None = None) -> list[Path]:
    """Files below root with the given extensions (case-insensitive), sorted by path.

    under: only inside this folder, relative to root (either slash).
    match: shell-style pattern on the file name without extension (case-insensitive).
    """
    root = Path(root)
    if not root.is_dir():
        from fpptools.errors import FppToolsError
        raise FppToolsError(f"Folder not found: {root}")
    exts = tuple(e.upper() for e in extensions)
    prefix = _norm(under) if under else ""
    pattern = match.casefold() if match else None
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort(key=str.casefold)
        rel_dir = _norm(os.path.relpath(dirpath, root))
        rel_dir = "" if rel_dir == "." else rel_dir
        if prefix and not (rel_dir == prefix or rel_dir.startswith(prefix + "/")):
            # outside the wanted folder: only descend towards it
            def leads_to_prefix(d: str) -> bool:
                child = f"{rel_dir}/{d.casefold()}".lstrip("/")
                return prefix == child or prefix.startswith(child + "/")
            dirnames[:] = [d for d in dirnames if leads_to_prefix(d)]
            continue
        for name in sorted(filenames, key=str.casefold):
            stem, ext = os.path.splitext(name)
            if ext.upper() in exts and (pattern is None or fnmatch.fnmatchcase(stem.casefold(), pattern)):
                found.append(Path(dirpath) / name)
    return found


def rel_folder(path: Path, root: Path) -> str:
    """Folder of path relative to root, Windows style ('' for files directly in root)."""
    parent = PurePath(os.path.relpath(Path(path).parent, root))
    return "" if str(parent) == "." else "\\".join(parent.parts)


# -- structure info (fast, no full parse) ------------------------------------------

@dataclass
class StrInfo:
    path: Path
    folder: str
    name: str
    unique_code: str
    description: str
    error: str = ""


def decode_description(text: str | None, b64: bool) -> str:
    if not text:
        return ""
    if not b64:
        return text.strip()
    raw = base64.b64decode("".join(text.split()), validate=False)
    return raw.decode(ENCODING, errors="replace").strip()


def read_info(path: Path, root: Path) -> StrInfo:
    path = Path(path)
    info = StrInfo(path, rel_folder(path, root), path.stem, "", "")
    tree_attrs: dict[str, str] | None = None
    try:
        for event, el in etree.iterparse(str(path), events=("start", "end"), strip_cdata=False,
                                         resolve_entities=False, huge_tree=True):
            if event == "start" and el.tag == "FP_TREE" and tree_attrs is None:
                tree_attrs = dict(el.attrib)
                info.unique_code = tree_attrs.get("NameStr", "")
            elif event == "end" and el.tag == "FP_DESCRIPTION" and tree_attrs is not None:
                info.description = decode_description(el.text, "DescrB64" in el.attrib)
                return info
            elif event == "end" and el.tag == "FP_TREE":
                break
            elif event == "end":
                el.clear()
    except (etree.XMLSyntaxError, OSError) as exc:
        info.error = f"cannot read: {exc}"
        return info
    except (binascii.Error, ValueError) as exc:
        info.error = f"bad description: {exc}"
        return info
    if tree_attrs is None:
        info.error = "no FP_TREE element"
    else:
        plain = tree_attrs.get("Description", "")
        if not plain.upper().startswith("SEE CDATA"):
            info.description = plain.strip()
    return info


# -- full parse / write (used by wipe) ---------------------------------------------
#
# Goal: an unchanged file must come back byte-identical, so a wipe only changes the
# lines it means to change. FP files mix several styles that a plain lxml round-trip
# would normalise, so parse() records them and serialize() restores them:
# - everything before/after the root element (declaration variants) is kept verbatim;
# - CR characters in text (CRLF and LF both occur, even inside one note) are protected
#   as &#13; so the parser cannot normalise them;
# - inside CDATA, line endings are per file (CRLF or LF), restored on write;
# - empty elements written as <X></X> stay so (lxml would write <X/>);
# - self-closing tags are <X/> in older files and <X /> in newer ones, per file.

@dataclass
class XmlDoc:
    path: Path
    tree: etree._ElementTree
    prolog: bytes        # original bytes before the root element
    epilog: bytes        # original bytes after the root element
    cdata_crlf: bool     # line endings inside CDATA
    spaced_empty: bool   # <X /> instead of <X/>


_EMPTY_PAIR = re.compile(rb"<([A-Za-z_][\w.:-]*)((?:\s[^<>]*)?)></\1>")
_EMPTY_MARK = "\u2063FPPTOOLS-EMPTY\u2063"   # invisible separator: not representable in cp1252
_EMPTY_REF = b"&#x2063;FPPTOOLS-EMPTY&#x2063;"
_CDATA = re.compile(rb"(<!\[CDATA\[.*?\]\]>)", re.S)
_TEXT = re.compile(rb">[^<]*<")
_ROOT_START = re.compile(rb"<[A-Za-z_]")


def _protect(markup: bytes) -> bytes:
    markup = _TEXT.sub(lambda m: m[0].replace(b"\r", b"&#13;"), markup)
    return _EMPTY_PAIR.sub(lambda m: b"<" + m[1] + m[2] + b">" + _EMPTY_REF + b"</" + m[1] + b">", markup)


def parse(path: Path) -> XmlDoc:
    raw = Path(path).read_bytes()
    start = _ROOT_START.search(raw)
    end = raw.rfind(b">") + 1
    if not start or end <= start.start():
        raise etree.XMLSyntaxError("no root element", None, 0, 0, str(path))
    prolog, body, epilog = raw[: start.start()], raw[start.start(): end], raw[end:]
    parts = _CDATA.split(body)
    markup = b"".join(parts[0::2])
    cdata = b"".join(parts[1::2])
    cdata_crlf = b"\r\n" in cdata if b"\n" in cdata else b"\r\n" in markup
    spaced = markup.count(b" />") > len(re.findall(rb"[^ ]/>", markup))
    protected = b"".join(p if i % 2 else _protect(p) for i, p in enumerate(parts))
    xml = b'<?xml version="1.0" encoding="windows-1252"?>\n' + protected
    parser = etree.XMLParser(strip_cdata=False, resolve_entities=False, huge_tree=True,
                             remove_blank_text=False)
    tree = etree.fromstring(xml, parser).getroottree()
    for el in tree.iter():
        if el.text == _EMPTY_MARK:
            el.text = ""
    return XmlDoc(Path(path), tree, prolog, epilog, cdata_crlf, spaced)


def _eol(data: bytes, crlf: bool) -> bytes:
    data = data.replace(b"\r\n", b"\n")
    return data.replace(b"\n", b"\r\n") if crlf else data


def serialize(doc: XmlDoc) -> bytes:
    """Bytes in the file's own FP style (see the notes above parse())."""
    body = etree.tostring(doc.tree.getroot(), encoding="windows-1252", xml_declaration=False,
                          with_tail=False)
    out = [doc.prolog]
    for i, p in enumerate(_CDATA.split(body)):
        if i % 2:  # CDATA block
            out.append(_eol(p, doc.cdata_crlf))
        else:      # lxml escapes '>' in text and attributes, so '/>' only ends tags
            if doc.spaced_empty:
                p = p.replace(b"/>", b" />")
            out.append(p.replace(b"&#13;", b"\r"))
    out.append(doc.epilog)
    return b"".join(out)
