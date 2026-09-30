"""Opt-in live call: pytest -m live. Costs ~$0.00002; recorded, so it replays afterwards."""

import pytest

from core.jev import Jev


@pytest.mark.live
def test_live_choice_and_noul_answer_shapes():
    out = Jev(mode="record", note="live smoke").ask(
        {"work_item": "Replace the consumer unit in a house in England"},
        {"route": {"type": "choice", "instructions": "Which route signs this work off under the Building Regulations?",
                   "criteria": {"competent_person": "Self-certified by a registered competent person",
                                "not_notifiable": "No notification needed"}},
         "notifiable": {"type": "noul", "instructions": "Is this work notifiable to building control?",
                        "criteria": {"true": "Notifiable", "false": "Not notifiable"}}})
    route, noul = out["answers"]["route"], out["answers"]["notifiable"]
    assert route["choice"] in ("competent_person", "not_notifiable")
    assert abs(sum(route["probabilities"].values()) - 1) < 0.01 and 0 <= route["confidence"] <= 1
    assert 0 <= noul["noul"] <= 1


@pytest.mark.live
def test_live_claude_judge_returns_a_known_label():
    from core.claude_judge import ClaudeJudge
    from packs.building_control.labels import LABELS
    out = ClaudeJudge(mode="record", note="live smoke").judge(
        {"work_item": "Replace the consumer unit", "project": "House in England"},
        "Which Building Regulations notification route applies?", LABELS)
    assert out["label"] in LABELS and abs(sum(out["probs"].values()) - 1) < 1e-6
