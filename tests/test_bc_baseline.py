import pytest

from packs.building_control.baseline import predict

HOUSE = "House in England"


@pytest.mark.parametrize("text,context,label", [
    ("Replace the consumer unit", HOUSE, "competent_person_scheme"),
    ("Add a socket outlet to an existing ring circuit in a living room", HOUSE, "not_notifiable"),
    ("Replace all windows with uPVC double glazing", HOUSE, "competent_person_scheme"),
    ("Rear extension sliding doors", HOUSE, "building_notice_or_full_plans"),
    ("Knocking through the wall with a steel beam", HOUSE, "building_notice_or_full_plans"),
    ("Kitchen extension built over the public sewer", HOUSE, "full_plans_required"),
    ("New partitions forming an escape corridor", "Office building in England", "full_plans_required"),
    ("Decoration walls and ceilings", HOUSE, "not_notifiable"),
    ("Office timber-frame walls", "Part of: detached single-storey garden office, under 15 m2", "not_notifiable"),
])
def test_keyword_baseline_good_and_bad_pairs(text, context, label):
    assert predict(text, context)[0] == label


def test_baseline_returns_a_probability_for_every_label():
    label, probs = predict("Skirtings", HOUSE)
    assert label == "not_notifiable" and abs(sum(probs.values()) - 1) < 1e-9 and len(probs) == 4
