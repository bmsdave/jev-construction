"""Phase 0 gate arms for "Is this work notifiable, and which route signs it off?".

A: Jev blind (item text and project context only).
B: BM25 top-k clauses -> Jev noul rerank (one call, one noul per clause) ->
   Jev answers with the best 1-3 clauses in `state`.
C: keyword baseline (no Jev).
"""

from packs.building_control.baseline import predict
from packs.building_control.labels import LABELS

JURISDICTION = "England. The Building Regulations 2010 as amended."
ROUTE = {
    "route": {
        "type": "choice",
        "instructions": "Under the Building Regulations 2010 in England, which notification route applies to this "
                        "work item if it is carried out on its own in the building described?",
        "criteria": LABELS,
    }
}
RERANK_INSTRUCTIONS = ("Does clause {cid} in candidate_clauses help decide which Building Regulations notification "
                       "route applies to the work item (exempt, self-certified by a competent person, building "
                       "notice or full plans)?")


def _item(row):
    return {"work_item": row["text"], "project": row["context"], "jurisdiction": JURISDICTION}


def _route(answer):
    a = answer["answers"]["route"]
    return {"label": a["choice"], "probs": a["probabilities"], "confidence": a.get("confidence") or 0.0}


def arm_a(row, jev):
    out = _route(jev.ask(_item(row), ROUTE))
    return {**out, "latency_s": jev.last["latency_s"], "cost_usd": jev.last["cost_usd"]}


def arm_b(row, jev, bm25, k_retrieve=10, k_keep=3):
    hits = bm25.search(f"{row['text']} {row['context']}", k=k_retrieve)
    cands = {f"c{i}": c for i, (c, _) in enumerate(hits, 1)}
    latency = cost = 0.0
    if cands:
        state = {**_item(row), "candidate_clauses": {cid: {"ref": c.ref,
                                                           "document": c.doc, "text": c.text}
                                                     for cid, c in cands.items()}}
        questions = {cid: {"type": "noul", "instructions": RERANK_INSTRUCTIONS.format(cid=cid),
                           "criteria": {"true": "The clause states a rule, exemption or scheme that applies to this "
                                                "kind of work.",
                                        "false": "The clause is about something else."}} for cid in cands}
        nouls = jev.ask(state, questions)["answers"]
        latency, cost = jev.last["latency_s"], jev.last["cost_usd"]
        ranked = sorted(cands, key=lambda cid: -nouls[cid]["noul"])
    else:
        ranked = []
    kept = [cands[cid] for cid in ranked[:k_keep]]
    state = {**_item(row), "clauses": [{"ref": c.ref, "document": c.doc, "text": c.text} for c in kept]}
    out = _route(jev.ask(state, ROUTE))
    return {**out, "retrieved": [c.id for c in cands.values()], "reranked": [cands[c].id for c in ranked],
            "kept": [c.id for c in kept], "latency_s": latency + jev.last["latency_s"],
            "cost_usd": cost + jev.last["cost_usd"]}


def arm_oracle(row, jev, index_by_id, k_keep=3):
    """Diagnostic only (not a gate arm): the labelled gold clauses in state, i.e. perfect retrieval.

    Gold clauses were chosen together with the label, so this is an upper bound on what
    better retrieval could give, not a fair estimate."""
    kept = [index_by_id[i] for i in row["gold_clauses"].split(";")][:k_keep]
    state = {**_item(row), "clauses": [{"ref": c.ref, "document": c.doc, "text": c.text} for c in kept]}
    out = _route(jev.ask(state, ROUTE))
    return {**out, "kept": [c.id for c in kept], "latency_s": jev.last["latency_s"], "cost_usd": jev.last["cost_usd"]}


def _judged(out, judge):
    return {**out, "latency_s": judge.last["latency_s"], "cost_usd": judge.last["cost_usd"]}


def arm_d(row, judge, clauses):
    """Claude as judge with the same clauses arm B kept: the ceiling for this retrieval."""
    state = {**_item(row), "clauses": [{"ref": c.ref, "document": c.doc, "text": c.text} for c in clauses]}
    return _judged(judge.judge(state, ROUTE["route"]["instructions"], LABELS), judge)


def arm_d_blind(row, judge):
    """Claude from its own knowledge, no clauses."""
    return _judged(judge.judge(_item(row), ROUTE["route"]["instructions"], LABELS), judge)


def arm_c(row):
    label, probs = predict(row["text"], row["context"])
    return {"label": label, "probs": probs, "confidence": max(probs.values()), "latency_s": 0.0, "cost_usd": 0.0}
