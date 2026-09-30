from packs.building_control.run_gate import decide, evaluate

LABELS = ["not_notifiable", "competent_person_scheme", "building_notice_or_full_plans", "full_plans_required"]


def pred(label, conf=0.9):
    probs = {l: (conf if l == label else (1 - conf) / 3) for l in LABELS}
    return {"label": label, "probs": probs, "confidence": conf, "latency_s": 0.4, "cost_usd": 0.00002,
            "kept": ["g"], "retrieved": ["g", "h"], "reranked": ["g", "h"]}


def rows(n):
    return [{"id": f"r{i}", "label": LABELS[i % 4], "split": "test" if (i // 4) % 2 else "train", "gold_clauses": "g"}
            for i in range(n)]


def test_evaluate_reports_per_arm_metrics_on_the_test_split_and_paired_difference():
    rs = rows(80)
    preds = {"A": {r["id"]: pred(LABELS[0]) for r in rs},
             "B": {r["id"]: pred(r["label"]) for r in rs},
             "C": {r["id"]: pred(r["label"] if int(r["id"][1:]) % 4 else LABELS[1]) for r in rs}}
    m = evaluate(rs, preds)
    assert m["arms"]["B"]["test"]["accuracy"] == 1.0
    assert m["arms"]["A"]["test"]["accuracy"] == 0.25
    assert m["arms"]["B"]["test"]["n"] == 40
    assert m["compare"]["B-C"]["diff"] > 0
    assert m["arms"]["B"]["retrieval"]["recall@1_reranked"] == 1.0
    assert m["arms"]["B"]["cost_usd_per_row"] > 0 and "roc_auc_notifiable" in m["arms"]["B"]["test"]


def test_gate_goes_only_when_b_beats_c_with_ci_above_zero_and_calibration_is_acceptable():
    ok = {"compare": {"B-C": {"diff": 0.1, "lo": 0.02, "hi": 0.2}},
          "arms": {"B": {"test": {"ece_binned": 0.05}}}}
    assert decide(ok)[0] is True
    assert decide({**ok, "compare": {"B-C": {"diff": 0.1, "lo": -0.01, "hi": 0.2}}})[0] is False
    assert decide({**ok, "arms": {"B": {"test": {"ece_binned": 0.3}}}})[0] is False


def test_reference_rows_are_scored_separately_and_never_used_for_fitting():
    rs = rows(80) + [{"id": f"ref{i}", "label": LABELS[i % 4], "split": "reference", "gold_clauses": "g"}
                     for i in range(8)]
    preds = {a: {r["id"]: pred(r["label"]) for r in rs} for a in ("A", "B", "C")}
    m = evaluate(rs, preds)
    assert m["arms"]["B"]["reference"]["n"] == 8 and m["arms"]["B"]["test"]["n"] == 40
    assert "B-C" in m["compare_reference"]
