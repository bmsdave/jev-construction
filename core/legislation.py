"""Clauses from legislation.gov.uk XML (Crown copyright, OGL v3).

Granularity: each numbered sub-paragraph directly under a top-level paragraph
(e.g. reg 12(6A), Sch 4 para 1(f)) is one clause, prefixed with the parent's
lead-in text; a paragraph with no sub-paragraphs is one clause; each numbered
row of a schedule table is one clause. Versions for other extents (e.g. Wales),
commentary and repealed text (". . . .") are dropped.
"""

import re
import xml.etree.ElementTree as ET

from core.clause import Clause

SKIP = {"Commentaries", "CommentaryRef", "Metadata", "Title"}
NUMBERED = {"P1", "P2", "P3", "P4"}
SPLIT_ABOVE = 4  # a paragraph with more sub-paragraphs than this is a list of alternatives: one clause each
SITE = "https://www.legislation.gov.uk/uksi/2010/2214/"


def _tag(e):
    return e.tag.rsplit("}", 1)[-1]


def _text(e, stop=()):
    """Readable text of e: sub-paragraph numbers become "(a)", table cells are joined by " | "."""
    out = []

    def walk(x):
        name = _tag(x)
        if name in SKIP or x in stop:
            pass
        elif name == "Pnumber":
            out.append(f" ({''.join(x.itertext()).strip()}) ")
        else:
            out.append(x.text or "")
            for c in x:
                walk(c)
            if name in ("td", "th"):
                out.append(" | ")
        out.append(x.tail or "")

    walk(e)
    return " ".join("".join(out).split()).strip(" |")


def _is_repealed(text):
    return not re.sub(r"^\(\w+\)", "", text).replace(".", "").strip()


def _path(e):
    return re.sub(r"^.*?/id/[a-z]+/\d{4}/\d+/", "", e.get("IdURI"))


def _ref(path):
    """'regulation/12/6A' -> 'reg 12(6A)'; 'schedule/4/paragraph/1/f' -> 'Sch 4 para 1(f)'."""
    kind, num, *rest = path.split("/")
    head = {"regulation": "reg", "schedule": "Sch"}.get(kind, kind) + f" {num}"
    if rest[:1] == ["part"]:
        head, rest = f"{head} Part {rest[1]}", rest[2:]
    if rest[:1] == ["paragraph"]:
        head, rest = f"{head} para {rest[1]}", rest[2:]
    return head + "".join(f"({p})" for p in rest)


def _slug(ref):
    return re.sub(r"[^A-Za-z0-9]+", "-", ref.replace("Sch", "sch")).strip("-")


def clauses_from_xml(xml_text, doc, extent="E", licence="OGL-3.0"):
    out, seen = [], set()

    def add(ref, text, url):
        if ref not in seen and not _is_repealed(text):
            seen.add(ref)
            out.append(Clause(id=f"{doc}:{_slug(ref)}", doc=doc, ref=ref, text=text, url=url, licence=licence))

    def children_of(p1):
        depth = len(_path(p1).split("/")) + 1
        return [c for c in p1.iter() if _tag(c) in NUMBERED and c.get("IdURI") and c is not p1
                and len(_path(c).split("/")) == depth]

    heading = [""]  # last un-numbered table row, e.g. "Loading" above requirement A1

    def visit(e, schedule):
        name = _tag(e)
        if name == "Commentaries" or (e.get("RestrictExtent") and extent not in e.get("RestrictExtent").split("+")):
            return
        if name == "Schedule" and e.get("IdURI"):
            schedule = _path(e)
        if name == "tr":
            row = _text(e)
            para, req = re.match(r"(\d+[A-Z]?)\.\s", row), re.match(r"([A-S]\d+[A-Z]?)\.", row)
            if schedule and para:
                add(f"{_ref(schedule)} para {para.group(1)}", row, SITE + schedule)
            elif schedule and req:
                add(f"{_ref(schedule)} {req.group(1)}", f"{heading[0]}: {row}" if heading[0] else row,
                    SITE + schedule)
            elif " | " not in row:
                heading[0] = row
            return
        if name == "P" and e.get("IdURI") and "/paragraph/wrapper" in e.get("IdURI"):
            part = _path(e).split("/paragraph/")[0]  # unnumbered paragraph: cite the enclosing Part (Class)
            add(_ref(part), _text(e), SITE + part)
            return
        if name == "P1" and e.get("IdURI"):
            kids = children_of(e)
            if len(kids) <= SPLIT_ABOVE:
                kids = []
            if not kids:
                add(_ref(_path(e)), _text(e), SITE + _path(e))
            own_number = [c for c in e if _tag(c) == "Pnumber"]
            lead = _text(e, stop=set(kids) | set(own_number))
            for c in kids:
                if not _is_repealed(_text(c)):
                    add(_ref(_path(c)), f"{lead} {_text(c)}".strip(), SITE + _path(c))
        for c in e:
            visit(c, schedule)

    visit(ET.fromstring(xml_text), "")
    return out
