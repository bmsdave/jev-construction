"""The committed Building Control clause index covers the rules the gate question needs."""

from pathlib import Path

from core.clause import load_jsonl

INDEX = Path(__file__).parents[1] / "packs" / "building_control" / "clauses" / "index.jsonl"


def test_index_has_the_clauses_that_decide_notifiability():
    refs = {(c.doc, c.ref) for c in load_jsonl(INDEX)}
    for need in [("BR2010", "reg 12(6)"), ("BR2010", "reg 12(6A)"), ("BR2010", "Sch 3 para 8"),
                 ("BR2010", "Sch 3 para 10"), ("BR2010", "Sch 4 para 2"), ("BR2010", "Sch 4 para 1(j)"),
                 ("BR2010", "Sch 2 Part 6 para 1"), ("BR2010", "Sch 1 P1"), ("ADP2013", "para 2.5"),
                 ("ADL1-2021", "para 0.3"), ("ADF1-2021", "para 0.3"), ("ADB1-2019", "para 0.1"),
                 ("ADA2013", "para 1.1")]:
        assert need in refs, need


def test_every_clause_is_citable_and_licensed():
    clauses = load_jsonl(INDEX)
    assert len({c.id for c in clauses}) == len(clauses)
    for c in clauses:
        assert c.text and c.url.startswith("https://") and c.licence == "OGL-3.0", c.id
