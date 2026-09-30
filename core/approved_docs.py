"""Clauses from the text of an Approved Document (pdftotext reading order, OGL v3).

A clause is one numbered paragraph ("2.5 ...") of the chosen sections. It runs
until the next numbered paragraph or "Section N" heading; page furniture
(page numbers, "ONLINE VERSION", running titles) is dropped.
"""

import re

from core.clause import Clause

PARA = re.compile(r"^(\d{1,2})\.(\d{1,2})(\s+[A-Z(‘“']|$)")  # real paragraphs start with a capital
SECTION = re.compile(r"^Section \d+")
MAX_CHARS = 1500
FURNITURE = re.compile(r"^(ONLINE VERSION|Approved Document [A-S]\b.*|\d{1,3}|[A-S]\d?/?\d?)$")


def clauses_from_text(text, doc, sections, url, licence="OGL-3.0"):
    found = {}
    current = None
    for raw in text.splitlines():
        line = raw.strip()
        m = PARA.match(line)
        if m or SECTION.match(line):
            current = None
            if m and m.group(1) in sections:
                current = [f"{m.group(1)}.{m.group(2)}", [line]]
                ref = current[0]
                # the same number can reappear (contents, cross-references): keep the longest text
                found.setdefault(ref, []).append(current[1])
            continue
        if current and line and not FURNITURE.match(line):
            current[1].append(line)
    out = []
    for ref, variants in found.items():
        body = " ".join(" ".join(max(variants, key=lambda v: len(" ".join(v)))).split())
        if len(body) > MAX_CHARS:
            body = body[:MAX_CHARS - 2].rsplit(" ", 1)[0] + " …"
        out.append(Clause(id=f"{doc}:para-{ref.replace('.', '-')}", doc=doc, ref=f"para {ref}", text=body,
                          url=url, licence=licence))
    return out
