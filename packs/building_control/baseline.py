"""Arm C: a deliberately simple keyword baseline for the notification-route question.

Rules are written from the vocabulary of reg 12, Schedules 2-4 and AD P, not
fitted to rows. Precedence: full-plans triggers, then structural/extension
words in the item, then Schedule 3 words, then Schedule 4 / non-work words;
anything else defaults to not_notifiable (the most common label).
"""

import re

from packs.building_control.labels import LABELS

NON_DOMESTIC = r"\b(office building|shop|retail|warehouse|restaurant|caf[eé]|school|hotel|surgery|care home|hall|" \
               r"leisure|pub|block of flats|flats|multiple occupation|hmo|nursery|barn|mixed-use)\b"
FULL_PLANS = r"\b(sewer|private (road|street)|unadopted)\b"
EXEMPT = r"\b(garden office|shed|conservatory|porch|awning|carport|fence|patio|path|deck|paving|permeable)\b"
STRUCTURAL = r"\b(extension|loft conversion|dormer|structural|steel|beam|joist|foundation|underpin\w*|drain\w*|" \
             r"inspection chamber|stair\w*|fire.?stop\w*|fire protection|party wall|chimney|basement|" \
             r"garage conver\w*|loadbearing|load-bearing|lintel|padstone|sleeper wall|reinforcement|" \
             r"temporary works|bearings|bolts|anchors|plates)\b"
SCHEDULE_4 = r"\b(existing (ring |radial )?circuit|replac\w+ (a |the )?(sink|bath|basin|wc|toilet|shower|gutter|" \
             r"downpipe|external door|back door)|gutters?|downpipes?|rain pipes|data|fibre|network|cat6a?|" \
             r"low-voltage|extra-low|alarm with low|telephone|decorat\w*|tiling|skirting\w*|floor finish\w*|" \
             r"floors|joinery|kitchen units|kitchen and island|appliances|skim|plaster\w*|loft floor|spurs?|" \
             r"sockets?|switch\w*|light fitting|luminaires|valve|isolator)\b"
SCHEDULE_3 = r"\b(windows?|doors?|rooflight|roof window|re-?roof|re-?tile|roof covering|boiler|heat.?pump|" \
             r"cylinder|ufh|underfloor|heating|pipework|pipe|cable|circuit|consumer unit|distribution board|" \
             r"solar|pv|stove|oil|cavity|wall insulation|mvhr|ventilation|shower|wcs?|basins?|softener|" \
             r"towel rails?|smoke|fan coils|manifolds?|thermostats?|actuators?|collectors?|wastes?|soil)\b"
SURE, REST = 0.85, 0.05


def _probs(label):
    return {k: SURE if k == label else REST for k in LABELS}


def predict(text, context=""):
    t, c = text.lower(), context.lower()
    if re.search(FULL_PLANS, t) or re.search(NON_DOMESTIC, c) or re.search(NON_DOMESTIC, t):
        label = "full_plans_required"
    elif re.search(EXEMPT, t) or re.search(EXEMPT, c):
        label = "not_notifiable"
    elif re.search(STRUCTURAL, t):
        label = "building_notice_or_full_plans"
    elif re.search(SCHEDULE_4, t):
        label = "not_notifiable"
    elif re.search(SCHEDULE_3, t):
        label = "competent_person_scheme"
    else:
        label = "not_notifiable"
    return label, _probs(label)
