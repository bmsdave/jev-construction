from core.clause import Clause
from core.retrieve import BM25
from packs.building_control.gate import arm_a, arm_b, arm_c

ROW = {"id": "x1", "text": "Replace the consumer unit", "context": "House in England"}
INDEX = [Clause("BR2010:reg-12-6A", "BR2010", "reg 12(6A)", "the replacement of a consumer unit is notifiable"),
         Clause("BR2010:sch-3-para-8", "BR2010", "Sch 3 para 8", "fixed low voltage electrical installations, consumer unit"),
         Clause("BR2010:sch-4-para-2", "BR2010", "Sch 4 para 2", "adding socket outlets to an existing circuit, not a consumer unit"),
         Clause("BR2010:reg-3", "BR2010", "reg 3", "building work means the erection or extension of a building")]


class FakeJev:
    """Answers route with CPS; rerank nouls favour reg 12(6A) then Sch 3 para 8."""

    def __init__(self):
        self.states, self.last = [], {"latency_s": 0.3, "cost_usd": 0.00002, "replayed": True}

    def ask(self, state, questions):
        self.states.append((state, questions))
        if "route" in questions:
            probs = {"competent_person_scheme": 0.7, "not_notifiable": 0.1, "building_notice_or_full_plans": 0.1,
                     "full_plans_required": 0.1}
            return {"answers": {"route": {"type": "choice", "choice": "competent_person_scheme",
                                          "probabilities": probs, "confidence": 0.6}}}
        cands = state["candidate_clauses"]
        score = {"reg 12(6A)": 0.9, "Sch 3 para 8": 0.8, "Sch 4 para 2": 0.4}
        return {"answers": {q: {"type": "noul", "noul": score.get(cands[q]["ref"], 0.05)} for q in questions}}


def test_arm_a_is_blind_and_returns_label_probabilities_and_confidence():
    jev = FakeJev()
    out = arm_a(ROW, jev)
    assert out["label"] == "competent_person_scheme" and out["confidence"] == 0.6
    assert out["probs"]["not_notifiable"] == 0.1 and out["latency_s"] == 0.3
    state = jev.states[0][0]
    assert "Replace the consumer unit" in str(state) and "clauses" not in str(state)


def test_arm_b_reranks_retrieved_clauses_and_answers_with_the_best_ones_in_state():
    jev = FakeJev()
    out = arm_b(ROW, jev, BM25(INDEX), k_retrieve=3, k_keep=2)
    assert out["retrieved"][:1] and set(out["retrieved"]) <= {c.id for c in INDEX}
    assert out["kept"] == ["BR2010:reg-12-6A", "BR2010:sch-3-para-8"]
    rerank_state, answer_state = jev.states[0][0], jev.states[1][0]
    assert len(jev.states[0][1]) == len(out["retrieved"])
    assert [c["ref"] for c in answer_state["clauses"]] == ["reg 12(6A)", "Sch 3 para 8"]
    assert out["label"] == "competent_person_scheme" and out["latency_s"] == 0.6


def test_arm_c_is_the_keyword_baseline():
    assert arm_c(ROW)["label"] == "competent_person_scheme"


def test_oracle_arm_puts_the_gold_clauses_in_state_to_measure_jev_without_retrieval_errors():
    from packs.building_control.gate import arm_oracle
    jev = FakeJev()
    out = arm_oracle({**ROW, "gold_clauses": "BR2010:sch-3-para-8;BR2010:reg-12-6A"}, jev, {c.id: c for c in INDEX})
    assert [c["ref"] for c in jev.states[0][0]["clauses"]] == ["Sch 3 para 8", "reg 12(6A)"]
    assert out["label"] == "competent_person_scheme" and out["kept"] == ["BR2010:sch-3-para-8", "BR2010:reg-12-6A"]


class FakeJudge:
    def __init__(self):
        self.calls, self.last = [], {"latency_s": 1.5, "cost_usd": 0.01, "replayed": True}

    def judge(self, state, question, labels):
        self.calls.append((state, question, labels))
        return {"label": "competent_person_scheme", "probs": {k: 0.25 for k in labels}, "confidence": 0.25}


def test_arm_d_gives_claude_the_same_clauses_arm_b_kept_and_d_blind_gives_none():
    from packs.building_control.gate import arm_d, arm_d_blind
    judge = FakeJudge()
    out = arm_d(ROW, judge, [INDEX[1], INDEX[0]])
    state, question, labels = judge.calls[0]
    assert [c["ref"] for c in state["clauses"]] == ["Sch 3 para 8", "reg 12(6A)"] and len(labels) == 4
    assert out["label"] == "competent_person_scheme" and out["cost_usd"] == 0.01 and out["latency_s"] == 1.5
    arm_d_blind(ROW, judge)
    assert "clauses" not in judge.calls[1][0]
