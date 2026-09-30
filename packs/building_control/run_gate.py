"""Run the Phase 0 gate: three arms on the same rows, metrics, go/no-go.

    python3 -m packs.building_control.run_gate --mode record   # live calls, recorded, spend-capped
    python3 -m packs.building_control.run_gate                 # replay only (offline)

Writes bench/runs/<run>/{predictions.csv,metrics.json,report.md}. Thresholds and
calibration are fitted on the train split and reported on the held-out test split.
"""

import argparse
import csv
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from core.claude_judge import ClaudeJudge
from core.calibrate import fit_binning, fit_threshold, selective
from core.clause import load_jsonl
from core.jev import Jev
from core.metrics import (accuracy, bootstrap_ci, brier, confusion, ece, macro_f1, paired_bootstrap_diff,
                          recall_at_k, roc_auc)
from core.retrieve import BM25
from packs.building_control.gate import arm_a, arm_b, arm_c, arm_d, arm_d_blind, arm_oracle
from packs.building_control.labels import LABELS
from packs.building_control.self_judge import load_answers

ROOT = Path(__file__).resolve().parents[2]
PACK = Path(__file__).resolve().parent
TARGET_ACCURACY = 0.9  # accepted answers must be at least this accurate on train
MAX_ECE = 0.1  # "acceptable calibration" after binning, on test


def _split_metrics(rs, p, labels):
    y = [r["label"] for r in rs]
    yp = [p[r["id"]]["label"] for r in rs]
    conf = [p[r["id"]]["confidence"] for r in rs]
    correct = [int(a == b) for a, b in zip(y, yp)]
    acc, lo, hi = bootstrap_ci(correct)
    return {"n": len(rs), "accuracy": acc, "accuracy_ci": [lo, hi], "macro_f1": macro_f1(y, yp, labels),
            "confusion": confusion(y, yp, labels), "brier": brier(y, [p[r["id"]]["probs"] for r in rs]),
            "ece": ece(conf, correct),
            "roc_auc_notifiable": roc_auc([int(l != "not_notifiable") for l in y],
                                          [1 - p[r["id"]]["probs"].get("not_notifiable", 0.0) for r in rs])}


def evaluate(rows, preds, labels=tuple(LABELS)):
    labels = list(labels)
    train = [r for r in rows if r["split"] == "train"]
    held_out = {"test": [r for r in rows if r["split"] == "test"],
                "reference": [r for r in rows if r["split"] == "reference"]}
    held_out = {k: v for k, v in held_out.items() if v}
    test = held_out["test"]
    out = {"labels": labels, "n_rows": len(rows), "arms": {}, "compare": {}}
    for arm, p in preds.items():
        m = {"all": _split_metrics(rows, p, labels),
             **{k: _split_metrics(v, p, labels) for k, v in held_out.items()},
             "cost_usd_per_row": sum(p[r["id"]]["cost_usd"] for r in rows) / len(rows),
             "latency_s_per_row": sum(p[r["id"]]["latency_s"] for r in rows) / len(rows)}
        tr_conf = [p[r["id"]]["confidence"] for r in train]
        tr_ok = [int(p[r["id"]]["label"] == r["label"]) for r in train]
        t = fit_threshold(tr_conf, tr_ok, TARGET_ACCURACY)
        cal = fit_binning(tr_conf, tr_ok)
        for split, rs in held_out.items():
            conf = [p[r["id"]]["confidence"] for r in rs]
            ok = [int(p[r["id"]]["label"] == r["label"]) for r in rs]
            cov, acc = selective(conf, ok, t)
            m[split].update({"threshold": t, "coverage_at_threshold": cov, "accuracy_at_threshold": acc,
                             "ece_binned": ece([cal(c) for c in conf], ok)})
        if "retrieved" in next(iter(p.values())):
            gold = [set(r["gold_clauses"].split(";")) for r in rows]
            m["retrieval"] = {f"recall@{k}_bm25": recall_at_k([p[r["id"]]["retrieved"] for r in rows], gold, k)
                              for k in (1, 3, 10)}
            m["retrieval"].update({f"recall@{k}_reranked": recall_at_k([p[r["id"]]["reranked"] for r in rows],
                                                                       gold, k) for k in (1, 3)})
        out["arms"][arm] = m
    pairs = [(a, b) for a, b in (("B", "C"), ("B", "A"), ("A", "C"), ("D", "C"), ("D", "B"), ("D_blind", "C"))
             if a in preds and b in preds]
    for split, rs in held_out.items():
        key = "compare" if split == "test" else f"compare_{split}"
        out[key] = {}
        for a, b in pairs:
            ca = [int(preds[a][r["id"]]["label"] == r["label"]) for r in rs]
            cb = [int(preds[b][r["id"]]["label"] == r["label"]) for r in rs]
            d, lo, hi = paired_bootstrap_diff(ca, cb)
            out[key][f"{a}-{b}"] = {"diff": d, "lo": lo, "hi": hi}
    return out


def decide(metrics):
    bc = metrics["compare"]["B-C"]
    ece_b = metrics["arms"]["B"]["test"]["ece_binned"]
    reasons = []
    if bc["lo"] <= 0:
        reasons.append(f"B does not beat C: accuracy diff {bc['diff']:+.3f}, 95% CI [{bc['lo']:+.3f}, {bc['hi']:+.3f}]")
    if ece_b > MAX_ECE:
        reasons.append(f"B calibration after binning ECE {ece_b:.3f} > {MAX_ECE}")
    return not reasons, reasons or [f"B beats C by {bc['diff']:+.3f} (CI [{bc['lo']:+.3f}, {bc['hi']:+.3f}]), "
                                    f"ECE after binning {ece_b:.3f}"]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="replay", choices=["replay", "record"])
    ap.add_argument("--run", default="phase0")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", help="output directory (default bench/runs/<run>)")
    ap.add_argument("--no-claude", action="store_true", help="skip arms D and D_blind (Claude as judge)")
    ap.add_argument("--self-judge", help="dir with answers_{blind,clauses}_*.jsonl from Claude Code subagents; "
                                         "used for D/D_blind instead of API calls")
    ap.add_argument("--claude-arms", default="D,D_blind", help="which Claude arms to run")
    ap.add_argument("--workers", type=int, default=3, help="parallel Claude calls")
    args = ap.parse_args(argv)
    rows = list(csv.DictReader((PACK / "bench" / "dataset.csv").open()))
    rows = rows[: args.limit] if args.limit else rows
    index = load_jsonl(PACK / "clauses" / "index.jsonl")
    bm25, by_id = BM25(index), {c.id: c for c in index}
    jev = Jev(mode=args.mode, note=f"gate {args.run}")
    preds = {"A": {}, "B": {}, "C": {}, "B_oracle": {}}
    for n, r in enumerate(rows, 1):
        preds["A"][r["id"]] = arm_a(r, jev)
        preds["B"][r["id"]] = arm_b(r, jev, bm25)
        preds["C"][r["id"]] = arm_c(r)
        preds["B_oracle"][r["id"]] = arm_oracle(r, jev, by_id)
        if n % 25 == 0:
            print(f"{n}/{len(rows)} rows, {jev.live_calls} live calls, ${jev.cost:.5f}", flush=True)
    if args.self_judge:
        preds["D"] = load_answers(sorted(Path(args.self_judge).glob("answers_clauses_*.jsonl")))
        preds["D_blind"] = load_answers(sorted(Path(args.self_judge).glob("answers_blind_*.jsonl")))
        missing = [r["id"] for r in rows if r["id"] not in preds["D"] or r["id"] not in preds["D_blind"]]
        assert not missing, f"self-judge answers missing for {len(missing)} rows, e.g. {missing[:3]}"
    elif not args.no_claude:
        judge = ClaudeJudge(mode=args.mode, note=f"gate {args.run} claude")
        arms = {"D": lambda r: arm_d(r, judge, [by_id[i] for i in preds["B"][r["id"]]["kept"]]),
                "D_blind": lambda r: arm_d_blind(r, judge)}
        with ThreadPoolExecutor(args.workers) as ex:
            for name in args.claude_arms.split(","):
                preds[name] = dict(zip([r["id"] for r in rows], ex.map(arms[name], rows)))
        print(f"Claude: {judge.live_calls} live calls, ${judge.cost:.4f}", flush=True)
    metrics = evaluate(rows, preds)
    metrics["gate"] = dict(zip(("go", "reasons"), decide(metrics)))
    metrics["jev"] = {"live_calls": jev.live_calls, "replayed": jev.replayed, "cost_usd_this_run": jev.cost,
                      "model": jev.model}
    out = Path(args.out) if args.out else ROOT / "bench" / "runs" / args.run
    out.mkdir(parents=True, exist_ok=True)
    with (out / "predictions.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "split", "confidence_label", "label"] + [f"{a}_{k}" for a in preds
                                                                    for k in ("label", "confidence")] + ["B_kept"])
        for r in rows:
            w.writerow([r["id"], r["split"], r["confidence"], r["label"]]
                       + [x for a in preds for x in (preds[a][r["id"]]["label"],
                                                     round(preds[a][r["id"]]["confidence"], 3))]
                       + [";".join(preds["B"][r["id"]]["kept"])])
    (out / "metrics.json").write_text(json.dumps(metrics, indent=1))
    print(json.dumps({a: {k: metrics["arms"][a]["test"][k] for k in ("accuracy", "macro_f1", "ece", "ece_binned")}
                      for a in preds}, indent=1))
    print("compare:", json.dumps(metrics["compare"]))
    print("gate:", metrics["gate"])


if __name__ == "__main__":
    main()
