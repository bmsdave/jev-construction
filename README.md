# jev-construction

Pre-check renovation and construction files (estimate lines, specs, document sets) against UK building
rules with **Jev** (TypeSafe System One) plus deterministic code. It is a **triage tool**: it never
certifies, approves or signs anything. Building Control, the structural engineer, the registered
competent person (electrician issuing the EIC, Gas Safe engineer, MCS installer, …) remain the people
who sign off. Every finding cites the clause (document + paragraph) it relies on.

**Status: Phase 0 gate — NO-GO for the Jev-centred design; Claude as judge reaches 0.95–0.98 on an
independent, source-backed reference set.** See
[`docs/phase0-go-no-go.ru.md`](docs/phase0-go-no-go.ru.md) and [`bench/runs/phase0/report.md`](bench/runs/phase0/report.md).

## Layout

| Path | What |
|---|---|
| `core/` | clause model, legislation.gov.uk and Approved Document parsers, BM25, Jev client (record/replay, spend cap, ledger), metrics, calibration |
| `packs/building_control/` | labels, keyword baseline, gate arms, clause index + sources manifest, labelled benchmark |
| `bench/` | `recordings/` (every API response, replayed offline), `self_judge/` (Claude subagent judge inputs without labels, and answers), `spend.csv` ledger, `runs/` |
| `plugin/`, `mcp/` | not built yet: Phase 0 said stop |
| `private/` | gitignored; `private/.env` holds `OPENROUTER_API_KEY` |

## Use

```bash
python3 -m pytest                                   # offline, replays recordings
python3 -m pytest -m live                           # one opt-in live call (~$0.00002)
python3 -m packs.building_control.build_index --fetch   # rebuild the clause index (needs pdftotext)
python3 -m packs.building_control.run_gate --self-judge bench/self_judge   # replay the Phase 0 benchmark
python3 -m packs.building_control.run_gate --mode record --run NAME   # live, spend-capped at $5 total
```

Python 3.11+, stdlib only at runtime; `pytest` for tests; `pdftotext` (poppler) to rebuild the index.
Code: MIT. Rule text: see [`ATTRIBUTION.md`](ATTRIBUTION.md).
