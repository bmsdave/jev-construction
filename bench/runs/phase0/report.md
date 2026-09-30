# Phase 0 gate report — Building Control notification route

Question: *under the Building Regulations 2010 in England, which notification route applies to this work
item if carried out on its own?* Labels (from reg 3, 9, 12 and Schedules 2–4; see
`packs/building_control/labels.py`): `not_notifiable`, `competent_person_scheme`,
`building_notice_or_full_plans`, `full_plans_required`.

Jev: `typesafe/jev-1.13` (→ `jev-1.13-20260917`) via OpenRouter `/api/v1/systemone`, 2026-09-29.
Claude judge: Claude Code subagents (Opus 5.5) at no API cost, blind to labels (see arm D below).
Everything replays offline: `python3 -m packs.building_control.run_gate --self-judge bench/self_judge`
(checked by `tests/test_bc_replay.py`).

## Data (301 rows, `packs/building_control/bench/dataset.csv`)

| Split | Rows | Origin | Used for |
|---|---|---|---|
| train | 149 | 141 real estimate lines (item, trade, zone; no address/names/money) relabelled from legislation + 72 synthetic/official examples | thresholds, calibration |
| test | 64 | same pool, stratified 30% | gate decision |
| **reference** | **88** | work items whose answer is stated by an authoritative source, each with its URL | independent check |

Reference sources (all 56 URLs fetched and returned HTTP 200 on 2026-09-29; 3 claims spot-checked against
the page text): Planning Portal 22, legislation.gov.uk 9, LABC / LABC Front Door 11, Approved Documents P
and H 8, GOV.UK 9, councils and building control partnerships 20, NICEIC 4, ECA, Electrical Safety First,
Gas Safe Register, HETAS, OFTEC. Rows stored as our paraphrase + URL, not copied text. Two rows were dropped
because sources conflicted with each other or with the label rules (extra radiator; new bathroom).

| Label | train+test | reference |
|---|---|---|
| not_notifiable | 74 | 19 |
| competent_person_scheme | 60 | 30 |
| building_notice_or_full_plans | 45 | 16 |
| full_plans_required | 34 | 23 |

## Arms

- **A** Jev blind: item + project context → one Choice question.
- **B** BM25 top-10 over 336 clauses → Jev noul rerank (1 call, 10 nouls) → best 3 clauses in `state` → Choice.
- **C** keyword baseline, no model.
- **B_oracle** (diagnostic): the gold clauses in Jev's `state` (perfect retrieval; optimistic, gold chosen with the label).
- **D** Claude as judge with the same 3 clauses arm B kept. 8 subagents, ~38 rows each, reading
  `bench/self_judge/d8/clauses_N.md` only (no labels, gold clauses or rationale in the input; checked).
- **D_blind** Claude as judge from its own knowledge. 3 subagents on `bench/self_judge/blind_N.jsonl`.

## Results

### Reference set (n = 88, independent, source-backed)

| Arm | Accuracy (95% CI) | Macro-F1 | Brier | ECE binned | ROC AUC notifiable |
|---|---|---|---|---|---|
| A Jev blind | 0.602 (0.500–0.705) | 0.527 | 0.480 | 0.063 | 0.921 |
| B Jev + clauses | 0.705 (0.614–0.795) | 0.704 | 0.419 | 0.066 | 0.972 |
| C keywords | 0.693 (0.591–0.784) | 0.671 | 0.521 | 0.173 | 0.798 |
| B_oracle | 0.989 (0.966–1.000) | 0.988 | 0.085 | 0.081 | 1.000 |
| **D Claude + clauses** | **0.977 (0.943–1.000)** | 0.974 | 0.060 | 0.031 | 1.000 |
| **D_blind Claude** | **0.955 (0.909–0.989)** | 0.952 | 0.079 | 0.035 | 0.999 |

Paired bootstrap: B − C +0.011 (−0.125 … +0.136); D − C +0.284 (+0.193 … +0.375); D − B +0.273
(+0.170 … +0.375); D_blind − C +0.261 (+0.159 … +0.352).

### Test split (n = 64, labelled by us)

| Arm | Accuracy (95% CI) | Macro-F1 | Brier | ECE binned | ROC AUC | $/row | s/row |
|---|---|---|---|---|---|---|---|
| A | 0.625 (0.500–0.750) | 0.609 | 0.519 | 0.104 | 0.893 | 0.000025 | 0.32 |
| B | 0.625 (0.500–0.750) | 0.593 | 0.530 | 0.076 | 0.863 | 0.000212 | 0.64 |
| C | 0.828 (0.734–0.906) | 0.845 | 0.305 | 0.038 | 0.870 | 0 | 0 |
| B_oracle | 0.844 (0.750–0.938) | 0.858 | 0.245 | 0.026 | 0.982 | 0.000038 | 0.32 |
| D | 0.922 (0.844–0.984) | 0.931 | 0.188 | 0.096 | 0.978 | ≈0.01 via API* | ≈8* |
| D_blind | 0.875 (0.781–0.953) | 0.887 | 0.212 | 0.060 | 0.978 | ≈0.005 via API* | ≈8* |

\* Subagents cost no API money here; as a product feature via OpenRouter, Opus 5.5 measured ≈ $0.005–0.01
and ≈ 8 s per call (reasoning off), 20 requests/min on a new account.

Paired bootstrap on test: B − C −0.203 (−0.344 … −0.063); D − C +0.094 (−0.016 … +0.203); D − B +0.297
(+0.156 … +0.438).

Retrieval (all rows): BM25 recall@10 0.24; after Jev rerank recall@3 0.23 (on train+test rows).

Hybrid tried on paper: accept Jev B when confidence ≥ 0.79 (fitted on train), send the rest to Claude:
test 0.891 with 78% of rows escalated; reference 0.955 with 61% escalated. It saves few Claude calls and
loses accuracy against D alone.

## Gate

Rule: go only if B (Jev + retrieved clauses) beats C with a CI above zero and binned ECE ≤ 0.10.
**NO-GO for the Jev-centred design**: on test B − C = −0.20 (CI below zero); on the independent reference
set B ties C (+0.01, CI spans zero).

What the new arms show:
1. **Claude is the accurate judge.** On source-backed reference rows Claude is right 95–98% of the time,
   with or without clauses, and clearly beats both Jev and keywords (CI above zero).
2. **The keyword baseline was flattered by our own labels**: 0.83 on test, 0.69 on the reference set.
3. **Jev's problem is still retrieval plus rule knowledge**: with the right clauses (oracle) Jev reaches
   0.99 on reference, with BM25 clauses 0.70. Jev's binary "needs any notice" view is strong (AUC 0.97).

Caveats:
- The labels on test/train were written by Claude (this session), and the reference labels were assigned by
  Claude agents from the cited pages, so a Claude judge shares their reading of the rules. The reference
  set limits this because every row rests on an external statement, but it is not a fully independent
  human labelling. **Owner spot-check still pending** (`owner_spotcheck.csv`).
- The reference set skews to clear-cut cases published as examples; real estimate lines are vaguer
  (test D 0.92 vs reference 0.98).
- D answers come from subagents, not a pinned API model; they are recorded in `bench/self_judge/` and
  replay exactly, but a rerun by new agents could differ.

## Spend

Ledger `bench/spend.csv`: $5.004 of the $5 cap. Jev: $0.079. Claude via OpenRouter: $4.925, **all discarded**:
the first run set `max_tokens=300` while Opus 5.5 reasoning was on, so most answers came back empty
(`finish_reason: length`). Fixed (reasoning off by default; a truncated answer now raises
`TruncatedAnswer`), and the judge was then run as Claude Code subagents at no API cost.

Not done on purpose: embeddings, plugin/MCP scaffolding, the curated work-type → clause table.
