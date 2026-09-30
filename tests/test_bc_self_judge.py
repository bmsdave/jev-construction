import json

from core.clause import Clause
from packs.building_control.self_judge import export_batches, load_answers

ROWS = [{"id": f"r{i}", "text": f"work {i}", "context": "House in England", "label": "not_notifiable",
         "gold_clauses": "BR2010:reg-3", "rationale": "secret reason", "split": "test"} for i in range(5)]
C = Clause("BR2010:reg-3", "BR2010", "reg 3", "building work means ...")


def test_batches_carry_no_labels_rationale_or_gold_and_d_batches_carry_the_kept_clauses(tmp_path):
    export_batches(ROWS, {r["id"]: [C] for r in ROWS}, tmp_path, n_batches=2)
    blind = [json.loads(l) for f in sorted(tmp_path.glob("blind_*.jsonl")) for l in f.read_text().splitlines()]
    withc = [json.loads(l) for f in sorted(tmp_path.glob("clauses_*.jsonl")) for l in f.read_text().splitlines()]
    assert len(blind) == len(withc) == 5 and len(list(tmp_path.glob("blind_*.jsonl"))) == 2
    text = (tmp_path / "blind_1.jsonl").read_text() + (tmp_path / "clauses_1.jsonl").read_text()
    assert "not_notifiable" not in text and "secret" not in text and "gold" not in text
    assert "clauses" not in blind[0] and withc[0]["clauses"][0]["ref"] == "reg 3"


def test_answers_are_parsed_per_id_and_bad_ones_are_unparsed(tmp_path):
    (tmp_path / "answers_blind_1.jsonl").write_text(
        '{"id": "r0", "label": "not_notifiable", "probabilities": {"not_notifiable": 0.9, "competent_person_scheme": 0.1}}\n'
        '{"id": "r1", "label": "banana", "probabilities": {}}\n')
    got = load_answers(tmp_path.glob("answers_blind_*.jsonl"))
    assert got["r0"]["label"] == "not_notifiable" and abs(got["r0"]["confidence"] - 0.9) < 1e-9
    assert got["r1"]["label"] == "unparsed"


def test_clause_batches_are_also_written_as_markdown_with_short_lines_readable_in_full(tmp_path):
    long = Clause("BR2010:reg-12-6A", "BR2010", "reg 12(6A)", "word " * 800)
    export_batches(ROWS, {r["id"]: [long] for r in ROWS}, tmp_path, n_batches=2)
    md = (tmp_path / "clauses_1.md").read_text()
    assert "## r0" in md and "reg 12(6A)" in md and max(len(l) for l in md.splitlines()) <= 200
    assert "not_notifiable" not in md and "secret" not in md
