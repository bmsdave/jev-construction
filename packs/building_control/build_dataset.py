"""Build packs/building_control/bench/dataset.csv for the Phase 0 gate.

    python3 -m packs.building_control.build_dataset --scope PATH/scope200_line_table.csv

Scope lines come from a real renovation estimate; only item, trade and zone are
kept (no address, names or money). Their old AI-made labels are kept as
`candidate_label` for comparison only; `label` comes from labels_scope200.csv,
derived from the legislation. synthetic.csv adds realistic and official
examples so every label has at least 30 rows.
"""

import argparse
import csv
from pathlib import Path

from packs.building_control.labels import stratified_split

BENCH = Path(__file__).resolve().parent / "bench"
CONTEXT = "Renovation of a terraced house (dwelling) in England."
ZONES = {
    "HOUSE": "existing house",
    "EXTENSION": "new single-storey rear extension",
    "LOFT": "loft conversion with rear dormer",
    "OFFICE": "detached single-storey garden office, under 15 m2, no sleeping accommodation",
    "SITE": "garden and external works of the house",
    "WHOLE": "whole-house renovation including loft conversion and rear extension",
}
FIELDS = ["id", "text", "context", "label", "gold_clauses", "confidence", "rationale", "provenance",
          "candidate_label", "split"]


def scope_rows(house_rows, labels):
    out = []
    for lab in labels:
        n = int(lab["row"])
        h = house_rows[n - 1]
        out.append({"id": f"s{n:03d}", "text": h["item"],
                    "context": f"{CONTEXT} Trade: {h['trade']}. Part of: {ZONES[h['zone']]}.",
                    "label": lab["label"], "gold_clauses": lab["gold_clauses"], "confidence": lab["confidence"],
                    "rationale": lab["rationale"], "provenance": "house-scope200 (relabelled)",
                    "candidate_label": h["legal_key"]})
    return out


def reference_rows(refs):
    """Expert-sourced rows (bench/reference.csv): cited source, never used for fitting."""
    return [{"id": r["id"], "text": r["text"], "context": r["context"], "label": r["label"],
             "gold_clauses": r["gold_clauses"], "confidence": r["confidence"], "rationale": r["source_claim"],
             "provenance": f"reference: {r['source_org']} {r['source_url']}", "candidate_label": "",
             "split": "reference"} for r in refs]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", required=True, help="scope200_line_table.csv (read-only source)")
    args = ap.parse_args(argv)
    house = list(csv.DictReader(open(args.scope)))
    rows = scope_rows(house, list(csv.DictReader((BENCH / "labels_scope200.csv").open())))
    rows += [{**r, "candidate_label": ""} for r in csv.DictReader((BENCH / "synthetic.csv").open())]
    split = stratified_split(rows, share=0.3, seed=20260929)
    rows = [{**r, "split": split[r["id"]]} for r in rows]
    if (BENCH / "reference.csv").exists():
        rows += reference_rows(csv.DictReader((BENCH / "reference.csv").open()))
    with (BENCH / "dataset.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} rows -> {BENCH / 'dataset.csv'}")


if __name__ == "__main__":
    main()
