# Prompt for ChatGPT: migrate jev-construction to the Decision API and ship it as a ChatGPT app

Attach the repository (GitHub link or zip of `jev-construction`, commit `6717070` or later) and paste
everything below the line.

---

You are taking over an open-source project, **jev-construction** (MIT licence). Your job has two parts:
(1) migrate its model calls to the **Decision API**, and (2) ship it as an app/plugin in the
**ChatGPT marketplace**. You choose the strategy; I set the constraints and the evidence you must respect.

Reply to the owner in **Russian**, briefly (answer first, 5–10 lines, details in files). Write code, docs
and commit messages in English.

## 1. What the product is, and what it must never claim

- A **pre-check and triage tool** for people who already work in UK (England) renovation and construction:
  it reads their own files (estimate/scope lines, specs, document sets as text) and says which Building
  Regulations route applies and which clause says so.
- It **never certifies, approves or signs**. Every report names who signs for real: Building Control, the
  registered competent person (electrician issuing the EIC, Gas Safe engineer, FENSA installer, MCS
  installer…), the structural engineer. Duty holders have legal competence duties under the Building
  Safety Act 2022; the tool must not look like a substitute for them.
- Every finding cites **document + paragraph** (e.g. "BR2010 reg 12(6A)", "ADP2013 para 2.7").
- Text only. Numbers and geometry are checked by deterministic code, not by a model.

## 2. What exists in the repo (read these first)

| Path | What |
|---|---|
| `docs/phase0-go-no-go.ru.md`, `bench/runs/phase0/report.md` | the measured results; read before deciding anything |
| `core/` | stdlib Python: legislation.gov.uk XML and Approved Document parsers, BM25, a Jev client (record/replay by request hash, spend cap, CSV ledger), a Claude-judge client, metrics (accuracy, macro-F1, Brier, ECE, ROC AUC, paired bootstrap), calibration |
| `packs/building_control/` | labels (`labels.py`), keyword baseline, gate arms, clause index (336 OGL clauses, `clauses/index.jsonl`, sources in `clauses/sources.json`) |
| `packs/building_control/bench/` | `dataset.csv` (301 rows: 149 train, 64 test, **88 reference rows each backed by an authoritative URL**), `reference.csv`, `owner_spotcheck.csv` |
| `bench/recordings/`, `bench/self_judge/` | every recorded model answer; the benchmark replays offline |
| `tests/` | 74 offline tests + opt-in live tests (`pytest -m live`) |

Question the pack answers today: *"Under the Building Regulations 2010 in England, which notification
route applies to this work item?"* → `not_notifiable` | `competent_person_scheme` |
`building_notice_or_full_plans` | `full_plans_required`.

## 3. Evidence you must take into account (Phase 0, 2026-09-29)

| Arm | Reference set (88, source-backed) | Test (64, our labels) |
|---|---|---|
| A Jev blind | 0.60 | 0.63 |
| B BM25 → Jev rerank → Jev with 3 clauses | 0.70 | 0.63 |
| C keyword rules | 0.69 | 0.83 |
| Jev with the correct clauses (oracle) | 0.99 | 0.84 |
| D Claude as judge with the same 3 clauses | 0.98 | 0.92 |
| D Claude as judge, no clauses | 0.95 | 0.88 |

Conclusions so far: the Jev-centred pipeline failed its gate; the bottleneck is retrieval (BM25 recall@10
0.24), not Jev's answer given the right clause; a strong LLM judge is accurate; Jev is strong on the binary
"needs any notice" view (ROC AUC ≈ 0.97) and very cheap (≈ $0.0002/row, 0.3–0.6 s). Labels on train/test
and on the reference set were assigned by Claude (the reference ones from cited pages), so treat the
numbers as provisional until a human spot-check is done.

## 4. Part 1 — migrate to the Decision API

- "Decision API" here means the typed-decision endpoint for Jev (TypeSafe System One), today reachable as
  `POST https://openrouter.ai/api/alpha/decisions` or `POST https://openrouter.ai/api/v1/systemone`, body
  `{model, state, questions}`, question types `choice` / `score` / `noul`. **Check the current official
  docs first** (TypeSafe docs index `https://docs.typesafe.ai/llms.txt`, OpenRouter docs) — endpoints are
  alpha and may have changed. If "Decision API" turns out to mean a different or newer product (including
  an OpenAI one), say so, compare, and recommend.
- Keep: record/replay by request hash, the spend ledger and cap, key only from the environment or a
  gitignored `private/.env` (never printed or committed), the pinned model version, the offline test suite.
- Re-run the Phase 0 benchmark on the new endpoint and report whether the numbers changed. The reference
  set is the regression test.

## 5. Part 2 — ship it in the ChatGPT marketplace

- **Check the current official OpenAI docs before scaffolding** (the old "plugins" were retired; verify
  what is current — e.g. Apps SDK / MCP-based apps, the app directory, GPTs with Actions — and its
  submission and review rules). Do not rely on memory.
- The app must expose at least: check one work item; check a pasted list or an uploaded CSV of estimate
  lines; show each answer with its clause citation, confidence and "who signs this off"; say "unsure —
  ask Building Control" when confidence is low.
- Privacy: users upload their own project files; state what is sent to which API and keep nothing longer
  than needed. No personal data in logs.

## 6. Decide the strategy yourself (this is the open part)

Propose and justify, with cost/latency/accuracy estimates from the numbers above:
- **Where decisions happen**: e.g. deterministic rules + clause lookup first; Jev (Decision API) for cheap
  binary/typed decisions; the ChatGPT model itself as the judge for the route (it plays the role Claude
  played in arm D); or another split. Say which model answers the route question in the shipped app and why.
- **Retrieval**: e.g. a curated work-type → clause table, query expansion, embeddings, or letting the
  model pick clauses from the index. Target: recall@3 ≥ 0.8 on the benchmark before relying on it.
- **Packaging**: one app vs. app + separate MCP server reusable from Codex and Claude Code; hosting; auth.
- **What to cut** for a first release.
Write the choice as `docs/strategy.md` (one page, options considered, decision, risks). If a real
trade-off needs the owner, ask one short question instead of guessing.

## 7. Rules that still apply

- **TDD**: failing test first, watch it fail, minimal code, green suite. Tests run offline from recordings;
  one opt-in live smoke test per external API.
- **Licensing of rule text**: Approved Documents, Building Regulations 2010 and GPDO are Crown copyright
  under OGL v3 (store with attribution, see `ATTRIBUTION.md`). **BS 7671, Eurocodes and other BSI/CEN
  standards are copyrighted: clause numbers and your own one-line paraphrase only.** Guidance pages in
  `reference.csv` are stored as paraphrase + URL, never copied text.
- **Spend**: set a cap per phase in the ledger and ask the owner before raising it. Watch for truncated
  answers (reasoning tokens eating `max_tokens`) — this already wasted $4.93 once; fail loudly on them.
- Verify every claim with a command or measurement; report failures and skipped checks plainly. Small,
  debuggable changes; no gold-plating; say what you deliberately did not do.
- England only for now; other jurisdictions become separate packs later.

## 8. Deliverables for your first session

1. `docs/strategy.md` with your chosen strategy (section 6).
2. Decision API client migrated, tests green, Phase 0 benchmark re-run with a comparison table.
3. A minimal ChatGPT app (per the current official format) that runs the Building Control check end to end
   on a sample CSV, plus the steps and checklist for marketplace submission.
4. A short note in Russian for the owner: what you chose, numbers, cost per 100 lines, what is left.
