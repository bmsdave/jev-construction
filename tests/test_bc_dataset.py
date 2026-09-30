"""The labelled gate dataset is well-formed: legal labels, citable gold clauses, balanced, no money."""

import csv
import re
from collections import Counter
from pathlib import Path

from core.clause import load_jsonl
from packs.building_control.labels import LABELS

PACK = Path(__file__).parents[1] / "packs" / "building_control"
ROWS = list(csv.DictReader((PACK / "bench" / "dataset.csv").open()))


def test_labels_and_gold_clauses_exist_in_the_index():
    ids = {c.id for c in load_jsonl(PACK / "clauses" / "index.jsonl")}
    for r in ROWS:
        assert r["label"] in LABELS, r["id"]
        gold = r["gold_clauses"].split(";")
        assert gold and all(g in ids for g in gold), (r["id"], gold)
        assert r["rationale"] and r["confidence"] in ("high", "medium", "low"), r["id"]


def test_every_label_has_at_least_30_rows_and_a_held_out_share():
    by = Counter(r["label"] for r in ROWS)
    test = Counter(r["label"] for r in ROWS if r["split"] == "test")
    for label in LABELS:
        assert by[label] >= 30, (label, by[label])
        assert test[label] >= 8, (label, test[label])


def test_no_money_or_duplicate_ids_in_a_public_dataset():
    assert len({r["id"] for r in ROWS}) == len(ROWS)
    for r in ROWS:
        assert not re.search(r"£|GBP|\bUSD\b|\$\s?\d", r["text"] + r["context"]), r["id"]
