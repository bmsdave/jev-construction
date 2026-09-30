# Building Control pack (England)

Question: which Building Regulations notification route applies to a work item — `not_notifiable`,
`competent_person_scheme`, `building_notice_or_full_plans`, `full_plans_required` (definitions and
legal basis in `labels.py`).

**Not released.** Jev with retrieved clauses does not beat the keyword baseline; Claude as judge does
(reference set: D 0.98, D_blind 0.95, Jev B 0.70, keywords 0.69; see `../../bench/runs/phase0/report.md`).

| File | What |
|---|---|
| `clauses/sources.json` | official sources (OGL v3) and which sections are indexed |
| `clauses/index.jsonl` | 336 clauses: BR2010 regs 2–5, 9, 12, 23, Sch 1–4; AD A, B1, F1, L1, P scoping sections |
| `bench/labels_scope200.csv` | legislation-derived labels for 141 real estimate lines, with gold clause and confidence |
| `bench/synthetic.csv` | 72 realistic/official examples (full plans cases, AD P 2.7/2.8) |
| `bench/dataset.csv` | merged benchmark with train/test split (`build_dataset.py`) |
| `bench/reference.csv` | 88 source-backed rows (paraphrase + URL of Planning Portal, LABC, GOV.UK, councils, NICEIC, …) |
| `bench/owner_spotcheck.csv` | 30 rows for the owner to confirm |
| `baseline.py`, `gate.py`, `run_gate.py` | arm C, arms A/B/oracle, runner and gate rule |

Who signs for real: Building Control (local authority or registered building control approver), or the
registered competent person for Schedule 3 work. This pack only triages.
