# Attribution

The code is MIT-licensed (see `LICENSE`). Rule text is not ours and keeps its own licence.

## Crown copyright, Open Government Licence v3.0

Contains public sector information licensed under the
[Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
Stored and embedded (clause text in `packs/*/clauses/index.jsonl` and in `bench/recordings/`):

| Doc id | Source | Version used |
|---|---|---|
| BR2010 | The Building Regulations 2010 (SI 2010/2214), regs 2, 3, 4, 5, 9, 12, 23 and Schedules 1–4, England text, [legislation.gov.uk](https://www.legislation.gov.uk/uksi/2010/2214) | revised text fetched 2026-09-29 |
| ADA2013 | Approved Document A: Structure (2004 edition incorporating 2010 and 2013 amendments), Sections 1–2 | gov.uk PDF |
| ADB1-2019 | Approved Document B: Fire safety, Volume 1 Dwellings (2019 edition with amendments, 2026 print), Section 0 | gov.uk PDF |
| ADF1-2021 | Approved Document F: Ventilation, Volume 1 Dwellings (2021 edition), Sections 0 and 3 | gov.uk PDF |
| ADL1-2021 | Approved Document L: Conservation of fuel and power, Volume 1 Dwellings (2021 edition incorporating 2023 amendments), Sections 0, 10–12 | gov.uk PDF |
| ADP2013 | Approved Document P: Electrical safety – dwellings (2013 edition), Sections 0–3 | gov.uk PDF |

Exact source URLs are in `packs/building_control/clauses/sources.json`; every clause carries its own `url`.
ADF1 and ADL1 2026 editions (in force from 24 March 2027) are deliberately not used yet.

## Copyrighted standards (not stored)

BS 7671, Eurocodes and other BSI/CEN standards are copyrighted. This project may store only their
clause numbers and our own one-line paraphrase, never their text. Approved Document A lists Eurocode
titles; only those titles (published in the OGL document) appear in the index.

## Reference benchmark sources

`packs/building_control/bench/reference.csv` cites public guidance pages (Planning Portal, LABC, GOV.UK,
local authority building control, NICEIC, ECA, Electrical Safety First, Gas Safe Register, HETAS, OFTEC).
Each row stores only our own paraphrase of the page's statement and its URL; no page text is copied.
