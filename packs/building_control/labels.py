"""Gate question labels, derived from the Building Regulations 2010 (England).

Precedence follows reg 12: work that consists only of Schedule 4 work, work to
an exempt building (reg 9, Schedule 2) or activity that is not "building work"
(reg 3) needs no notice; work in Schedule 3 may be self-certified by a
registered competent person (reg 12(6)(a)); otherwise a building notice or
full plans application is needed (reg 12(2)), and full plans only where
reg 12(3)-(5) applies (Fire Safety Order premises, private street, building
over a sewer under H4).
"""

import random

LABELS = {
    "not_notifiable": "No Building Regulations notice needed: not building work (reg 3), only Schedule 4 work, "
                      "or an exempt building (reg 9, Schedule 2).",
    "competent_person_scheme": "Notifiable work listed in Schedule 3: a registered competent person can "
                               "self-certify it (reg 12(6)(a)); otherwise a building notice is needed.",
    "building_notice_or_full_plans": "Building work not covered by Schedules 3 or 4: a building notice or a full "
                                     "plans application to building control (reg 12(2)).",
    "full_plans_required": "Building work that must have a full plans application: the Fire Safety Order "
                           "applies to the building (reg 12(3)), it fronts a private street (12(4)), or H4 "
                           "applies (building over or near a sewer, 12(5)).",
}


def stratified_split(rows, share=0.3, seed=0):
    """{id: 'train'|'test'}: round(share * n) rows of each label go to test."""
    rng = random.Random(seed)
    out = {}
    for label in sorted({r["label"] for r in rows}):
        ids = sorted(r["id"] for r in rows if r["label"] == label)
        rng.shuffle(ids)
        k = round(share * len(ids))
        out.update({i: "test" if n < k else "train" for n, i in enumerate(ids)})
    return out
