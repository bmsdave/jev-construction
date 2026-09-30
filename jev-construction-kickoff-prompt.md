# Kickoff prompt: `jev-construction` plugin

Paste everything below the line into the first session of the new project.

---

You are starting a new open project: **`jev-construction`**, one plugin for Claude Code and Codex that lets people who already work in renovation and construction use **Jev** (TypeSafe's System One decision model) from code or from their coding agent to pre-check their own files (scope/estimate lines, specs, document sets, plans exported as data) against building rules.

Reply to the owner in **Russian**, short (answer first, 5–10 lines, details in files). Write code, docs and commit messages in English.

## 1. What the product is, and what it must never claim

- It is a **pre-check and triage tool**. It never certifies, approves or signs anything. Every report states who must sign for real: Building Control, the structural engineer, the MCS installer, the electrician/tester issuing the EIC, the Gas Safe engineer, etc. UK duty holders have legal competence duties under the Building Safety Act 2022; the tool must not look like a substitute for them.
- Every finding cites the **clause it relies on** (document + paragraph number), so a human can check it.
- Jev reads **text only** (no drawings, no images) and **does not calculate**. Numbers and geometry are checked by deterministic code; Jev answers closed questions that need a judgement over text.

## 2. Architecture: one plugin, core plus discipline packs

```
parse files ─► deterministic rules ─► retrieve candidate clauses ─► Jev reranks clauses (noul per clause)
            ─► Jev answers the closed question with 1–3 chosen clauses in `state`
            ─► report; Claude writes explanations only for low-confidence rows
```

- **Core** (shared): file parsers (CSV/XLSX estimates, PDF text, IFC via IfcOpenShell later), clause index and retrieval (BM25 first; embeddings only if BM25 is measurably worse), Jev client with record/replay, threshold calibration, report format, benchmark harness, spend ledger.
- **Packs** (one per discipline), each shipping: question set, criteria, clause index, a labelled benchmark set, tuned thresholds and a published accuracy table. A pack is released only when it beats a simple keyword/rule baseline on its own benchmark.
- Pack order: (1) **Building Control**: which Approved Document parts apply, is the work notifiable, which competent-person scheme or sign-off is needed; (2) planning / permitted development; (3) plumbing and drainage (Parts G, H, Water Supply Regulations); (4) electrical (Part P only; BS 7671 by clause reference); (5) structural as **triage only** ("does this need an engineer, how risky"). **No interior/exterior design pack**: no standard to cite, and Jev failed exactly on taste and owner-intent items in earlier measurements.
- Distribution: one Claude Code plugin (skill + MCP server) and the same MCP server and skill usable from Codex. **Check the current plugin, marketplace and Codex skill/MCP formats in the official docs before scaffolding** (use context7 or the claude-code-guide agent); do not rely on memory.

## 3. Licensing of rule text

- Approved Documents (gov.uk), the Building Regulations 2010 and the GPDO (legislation.gov.uk) are Crown copyright under the **Open Government Licence v3**: may be stored and embedded with attribution. Keep an `ATTRIBUTION.md`.
- **BS 7671, Eurocodes, other BSI/CEN standards are copyrighted**: store clause numbers and our own one-line paraphrase only, never their text.
- Code licence: propose Apache-2.0 or MIT, confirm with the owner.

## 4. Jev facts already measured (2026-09-27/29, OpenRouter)

- Access through **OpenRouter**. Key: `OPENROUTER_API_KEY` in the environment, or `private/.env` (gitignored) in this repo; the owner copies it in. Never print or commit it.
- Endpoints: `POST https://openrouter.ai/api/v1/systemone` (TypeSafe-SDK shape) or `POST https://openrouter.ai/api/alpha/decisions`. Body `{model, state, questions}`. Pin `typesafe/jev-1.13` (resolves to `typesafe/jev-1.13-20260917`); bare `jev-1.13` also works on `/systemone`.
- Question types: `choice` (≤255 labelled options, returns choice + per-option probabilities + confidence), `score` (ordered 2–10 levels, fractional score + distribution), `noul` (calibrated yes/no, 0–1). Several questions per call share the `state` cost. No explanation text is returned.
- Cost ≈ $0.04 per million input tokens, output free; a 3-question call cost ≈ $0.00002; latency ≈ 0.35 s.
- Official agent skill: `typesafe-ai/skills` (plugin `typesafe@typesafe-ai`, already installed at user scope); docs index `https://docs.typesafe.ai/llms.txt`. SDKs: `typesafe_sdk` (Python), `@typesafe-ai/sdk` (TS), base URL `https://openrouter.ai/api`.
- A working stdlib client with retries, spend cap and ledger exists at `/Users/vadim/project/house_renovation/tools/scripts/ai_review.py` (class `Jev`). Port the pattern; do not import from that repo.
- **Measured accuracy (house repo, `tools/AI_REVIEW.md`)**: on 191 model-QA findings, Jev *blind* separated real defects from checker notes at ROC AUC **0.58** (near chance). A 95% figure "with context" came only from the checker's own status being in `state`, i.e. label leakage; a one-line rule scored 99%. So **it is not yet shown that putting rule text in `state` makes Jev accurate.** Also see "Jev Does Not Play Dice" (reported 82.9% confidence vs 19% actual on a fair die): never trust raw probabilities without calibration on our own labels.
- Useful references from awesome-jev: `abhixhek/jevcal` (threshold fitting), `anessbelbati/jev-rerank-bench` and `zhuyansen/jev-search-rerank-eval` (reranking evidence), `suraj-phanindra/wellposed` (linting Jev requests), `steven-shoemaker/hunch` (escalate unsure rows to an LLM).

## 5. Phase 0: the gate experiment. Do this first, build nothing else until it is decided

Question: **"Is this work notifiable to Building Control, and which route signs it off?"** Closed labels, e.g. `not_notifiable`, `competent_person_scheme`, `building_notice_or_full_plans`, `specialist_certificate_other` (refine from the legislation).

1. **Ground truth from legislation, not from AI.** Derive labels from Building Regulations 2010 **Schedule 3** (self-certification by competent-person schemes) and **Schedule 4** (work that needs no notice), plus reg. 12 and the Approved Document scoping text. Cite the paragraph for each label.
2. **Dataset.** Start from the 153 scope lines in `/Users/vadim/project/house_renovation/09-cost/SCOPE200/scope200_line_table.csv` (columns: phase, zone, trade, item, …, `diy_allowed`, `how`, `legal_key`). Their existing labels were produced by AI agents, so treat them as **candidates only**: relabel every row from step 1, and have the owner spot-check at least 30 rows. Strip the address, names and £ figures before committing (the owner allows sending everything to OpenRouter, but this repo is public). Add 50–100 more lines from public sources or synthetic but realistic UK renovation items so all labels have ≥30 examples; keep a held-out split.
3. **Three arms on the same rows:** (A) Jev blind (item text only); (B) Jev with 1–3 retrieved clauses in `state` (BM25 top-k → Jev `noul` rerank → answer); (C) deterministic keyword/rule baseline. Optional (D): the retrieved clause plus Claude as judge, to know the ceiling.
4. **Report:** accuracy, macro-F1, confusion matrix, ROC AUC for binary views, Brier/ECE, bootstrap 95% CIs, cost and latency per row, plus retrieval recall@k on its own (did the right clause reach Jev at all?).
5. **Gate:** go on only if (B) beats (C) by a margin whose CI excludes zero, with acceptable calibration after threshold tuning. Otherwise stop and report to the owner what failed (retrieval or Jev) and what would change the result.

Spend cap for Phase 0: **$5** total, tracked in a ledger file; record every Jev response so reruns replay offline.

## 6. Repository and engineering rules

- Layout suggestion: `core/`, `packs/building_control/{questions.yaml,clauses/,bench/,thresholds.json,README.md}`, `plugin/` (Claude Code plugin + marketplace manifest), `mcp/`, `bench/runs/`, `docs/`, `ATTRIBUTION.md`, `private/` (gitignored). Python stdlib-first; add a dependency only when it earns its place.
- Tests run offline with recorded Jev responses; one opt-in live smoke test. Every pack has good/bad example pairs and at least one case taken from a published official example.
- Verify each claim with a command or measurement; report failures and skipped checks plainly. Keep changes small and debuggable. No gold-plating: stop when the owner can decide, and say what you deliberately did not do.
- This project is separate from the house renovation; do not edit `/Users/vadim/project/house_renovation` (read-only source for the dataset and the client pattern).

## 7. First session deliverables

1. Repo skeleton, licence proposal, `.gitignore` with `private/`.
2. Clause index for Building Regulations 2010 Schedules 1, 3, 4 and the scoping sections of Approved Documents A, B, F, L, P (OGL, with attribution).
3. Labelled dataset (with provenance per label) and the three-arm benchmark results.
4. A one-page go/no-go note in Russian for the owner, with numbers.

Open decisions to confirm with the owner early: open source vs commercial, licence, UK-only first (recommended), repo name.
