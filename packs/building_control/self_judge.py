"""Arm D with Claude Code subagents as judge (no API cost), kept blind to the labels.

export_batches writes rows WITHOUT label, gold clauses or rationale; subagents answer
each row as JSON into answers_<kind>_<n>.jsonl; load_answers reads them back. The
answer files are committed, so the arm replays like any other recording.
"""

import json
import textwrap
from pathlib import Path

from core.claude_judge import parse
from packs.building_control.gate import JURISDICTION
from packs.building_control.labels import LABELS


def export_batches(rows, kept, out_dir, n_batches=3):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for b in range(n_batches):
        part = rows[b::n_batches]
        item = [{"id": r["id"], "work_item": r["text"], "project": r["context"], "jurisdiction": JURISDICTION}
                for r in part]
        (out_dir / f"blind_{b + 1}.jsonl").write_text("".join(json.dumps(x) + "\n" for x in item))
        with_c = [{**x, "clauses": [{"ref": c.ref, "document": c.doc, "text": c.text} for c in kept[r["id"]]]}
                  for x, r in zip(item, part)]
        (out_dir / f"clauses_{b + 1}.jsonl").write_text("".join(json.dumps(x) + "\n" for x in with_c))
        (out_dir / f"clauses_{b + 1}.md").write_text(_markdown(with_c))


def _markdown(items):
    """Same content as the JSONL, with lines short enough for an agent's file reader to show in full."""
    out = []
    for x in items:
        out += [f"## {x['id']}", f"work_item: {x['work_item']}", f"project: {x['project']}", ""]
        for c in x["clauses"]:
            out.append(f"### clause {c['document']} {c['ref']}")
            out += textwrap.wrap(c["text"], 180) + [""]
    return "\n".join(out) + "\n"


def load_answers(paths):
    out = {}
    for p in paths:
        for line in Path(p).read_text().splitlines():
            if line.strip():
                d = json.loads(line)
                out[d["id"]] = {**parse(json.dumps(d), LABELS), "latency_s": 0.0, "cost_usd": 0.0}
    return out
