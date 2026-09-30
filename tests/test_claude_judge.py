import csv
import json

import pytest

from core.claude_judge import ClaudeJudge

LABELS = {"yes_route": "Route one.", "no_route": "Route two."}


def chat(content, prompt_tokens=1000, completion_tokens=100, cost=None):
    usage = {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens}
    if cost is not None:
        usage["cost"] = cost
    return {"choices": [{"message": {"role": "assistant", "content": content}}], "usage": usage}


class FakeTransport:
    def __init__(self, *responses):
        self.responses, self.calls = list(responses), []

    def __call__(self, url, body, headers):
        self.calls.append((url, body, headers))
        return self.responses.pop(0)


def make(tmp_path, t, mode="record"):
    return ClaudeJudge(key="sk-test-SECRET", mode=mode, transport=t, cache_dir=tmp_path / "rec",
                       ledger=tmp_path / "spend.csv", cap_usd=5.0, sleep=lambda s: None)


def test_judge_sends_chat_request_and_parses_label_and_probabilities(tmp_path):
    t = FakeTransport(chat('```json\n{"label": "no_route", "probabilities": {"yes_route": 0.2, "no_route": 0.8}}\n```'))
    out = make(tmp_path, t).judge({"work_item": "Replace a sink"}, "Which route?", LABELS)
    assert out == {"label": "no_route", "probs": {"yes_route": 0.2, "no_route": 0.8}, "confidence": 0.8}
    url, body, headers = t.calls[0]
    assert url == "https://openrouter.ai/api/v1/chat/completions"
    assert body["model"] == "anthropic/claude-opus-5.5" and body["messages"][-1]["role"] == "user"
    assert "Replace a sink" in body["messages"][-1]["content"] and "no_route" in body["messages"][0]["content"]


def test_unknown_or_unparseable_answer_is_kept_as_unparsed_not_guessed(tmp_path):
    t = FakeTransport(chat("I think it depends."), chat('{"label": "maybe", "probabilities": {}}'))
    j = make(tmp_path, t)
    assert j.judge({"a": 1}, "Q?", LABELS)["label"] == "unparsed"
    assert j.judge({"a": 2}, "Q?", LABELS)["label"] == "unparsed"


def test_missing_cost_is_estimated_from_input_and_output_prices(tmp_path):
    make(tmp_path, FakeTransport(chat('{"label": "yes_route", "probabilities": {"yes_route": 1, "no_route": 0}}',
                                      prompt_tokens=1_000_000, completion_tokens=100_000))).judge({}, "Q?", LABELS)
    row = next(csv.DictReader((tmp_path / "spend.csv").open()))
    assert float(row["cost_usd"]) == pytest.approx(4.0 + 2.0) and row["estimated"] == "1"


def test_judge_replays_offline(tmp_path):
    make(tmp_path, FakeTransport(chat('{"label": "yes_route", "probabilities": {"yes_route": 0.9, "no_route": 0.1}}',
                                      cost=0.01))).judge({"x": 1}, "Q?", LABELS)
    again = make(tmp_path, FakeTransport(), mode="replay").judge({"x": 1}, "Q?", LABELS)
    assert again["label"] == "yes_route"


def test_truncated_answer_fails_loudly_instead_of_silently_counting_as_wrong(tmp_path):
    from core.claude_judge import TruncatedAnswer
    cut = {"choices": [{"message": {"content": ""}, "finish_reason": "length"}],
           "usage": {"prompt_tokens": 10, "completion_tokens": 300, "cost": 0.006}}
    with pytest.raises(TruncatedAnswer):
        make(tmp_path, FakeTransport(cut)).judge({}, "Q?", LABELS)


def test_reasoning_is_off_by_default_so_the_token_budget_goes_to_the_answer(tmp_path):
    t = FakeTransport(chat('{"label": "yes_route", "probabilities": {"yes_route": 1, "no_route": 0}}'))
    make(tmp_path, t).judge({}, "Q?", LABELS)
    assert t.calls[0][1]["reasoning"] == {"enabled": False}
