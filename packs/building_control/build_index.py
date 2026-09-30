"""Build packs/building_control/clauses/index.jsonl from official sources.

    python3 -m packs.building_control.build_index [--fetch]

--fetch downloads legislation XML and Approved Document PDFs into sources/
(gitignored); pdftotext (poppler) converts the PDFs. Everything is OGL v3.
"""

import argparse
import json
import subprocess
import urllib.request
from pathlib import Path

from core.approved_docs import clauses_from_text
from core.clause import save_jsonl
from core.legislation import clauses_from_xml

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOURCES = ROOT / "sources"
LEG = "https://www.legislation.gov.uk/uksi/2010/2214/{}/data.xml"


def _get(url, path):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=60) as r:
            path.write_bytes(r.read())


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    args = ap.parse_args(argv)
    manifest = json.loads((HERE / "clauses" / "sources.json").read_text())
    clauses = []
    for leg in manifest["legislation"]:
        for part in leg["parts"]:
            xml = SOURCES / f"bregs_{part.replace('/', '_')}.xml"
            if args.fetch:
                _get(LEG.format(part), xml)
            clauses += clauses_from_xml(xml.read_text(), doc=leg["doc"])
    for ad in manifest["approved_documents"]:
        pdf, txt = SOURCES / f"{ad['file']}.pdf", SOURCES / f"{ad['file']}.raw.txt"
        if args.fetch:
            _get(ad["url"], pdf)
        if not txt.exists() or txt.stat().st_mtime < pdf.stat().st_mtime:
            subprocess.run(["pdftotext", str(pdf), str(txt)], check=True)
        clauses += clauses_from_text(txt.read_text(), doc=ad["doc"], sections=set(ad["sections"]), url=ad["url"])
    seen, unique = set(), []
    for c in clauses:  # concurrent versions of one provision: keep the first (England) one
        if c.id not in seen:
            seen.add(c.id)
            unique.append(c)
    save_jsonl(unique, HERE / "clauses" / "index.jsonl")
    by_doc = {}
    for c in unique:
        by_doc[c.doc] = by_doc.get(c.doc, 0) + 1
    print(f"{len(unique)} clauses: {by_doc}")


if __name__ == "__main__":
    main()
