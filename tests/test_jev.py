import csv

import pytest

from core.jev import Jev, MissingRecording, SpendCapReached, TransientError, load_key

Q = {"notifiable": {"type": "noul", "instructions": "Is it notifiable?",
                    "criteria": {"true": "yes", "false": "no"}}}
ANSWER = {"answers": {"notifiable": {"type": "noul", "noul": 0.8}},
          "usage": {"input_tokens": 500, "output_tokens": 10, "cost": 0.00002}}


class FakeTransport:
    def __init__(self, *responses):
        self.responses, self.calls = list(responses), []

    def __call__(self, url, body, headers):
        self.calls.append((url, body, headers))
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def make(tmp_path, transport, mode="record", cap=5.0):
    return Jev(key="sk-test-SECRET", mode=mode, transport=transport, cache_dir=tmp_path / "rec",
               ledger=tmp_path / "spend.csv", cap_usd=cap, sleep=lambda s: None)


def test_record_then_replay_calls_api_once(tmp_path):
    t = FakeTransport(ANSWER)
    assert make(tmp_path, t).ask("replace consumer unit", Q)["answers"]["notifiable"]["noul"] == 0.8
    again = make(tmp_path, FakeTransport(), mode="replay").ask("replace consumer unit", Q)
    assert again["answers"]["notifiable"]["noul"] == 0.8
    assert len(t.calls) == 1


def test_replay_without_recording_fails_instead_of_calling_api(tmp_path):
    with pytest.raises(MissingRecording):
        make(tmp_path, FakeTransport(ANSWER), mode="replay").ask("new state", Q)


def test_spend_cap_stops_before_the_call(tmp_path):
    (tmp_path / "spend.csv").write_text("utc,request,input_tokens,cost_usd,estimated,note\nx,y,1,4.999,0,\n")
    t = FakeTransport(ANSWER)
    with pytest.raises(SpendCapReached):
        make(tmp_path, t, cap=5.0).ask("s", Q)
    assert t.calls == []


def test_each_live_call_is_ledgered_and_missing_cost_is_estimated_from_tokens(tmp_path):
    no_cost = {"answers": ANSWER["answers"], "usage": {"input_tokens": 1_000_000, "output_tokens": 5}}
    make(tmp_path, FakeTransport(no_cost)).ask("s", Q)
    rows = list(csv.DictReader((tmp_path / "spend.csv").open()))
    assert len(rows) == 1 and float(rows[0]["cost_usd"]) == pytest.approx(0.04) and rows[0]["estimated"] == "1"


def test_transient_errors_are_retried(tmp_path):
    t = FakeTransport(TransientError("429"), TransientError("503"), ANSWER)
    assert make(tmp_path, t).ask("s", Q)["answers"]["notifiable"]["noul"] == 0.8
    assert len(t.calls) == 3


def test_request_body_is_model_state_questions_and_key_only_in_header(tmp_path):
    t = FakeTransport(ANSWER)
    jev = make(tmp_path, t)
    jev.ask({"item": "x"}, Q)
    url, body, headers = t.calls[0]
    assert url == "https://openrouter.ai/api/v1/systemone"
    assert set(body) == {"model", "state", "questions"} and body["model"] == "typesafe/jev-1.13"
    assert headers["Authorization"] == "Bearer sk-test-SECRET"
    stored = "".join(p.read_text() for p in (tmp_path / "rec").rglob("*.json")) + (tmp_path / "spend.csv").read_text()
    assert "SECRET" not in stored and "SECRET" not in repr(jev)


def test_key_from_environment_wins_over_env_file(tmp_path):
    f = tmp_path / ".env"
    f.write_text("# comment\nexport OPENROUTER_API_KEY='from-file'\n")
    assert load_key(environ={}, env_file=f) == "from-file"
    assert load_key(environ={"OPENROUTER_API_KEY": "from-env"}, env_file=f) == "from-env"


def test_latency_and_cost_of_last_answer_are_kept_for_replayed_calls_too(tmp_path):
    make(tmp_path, FakeTransport(ANSWER)).ask("s", Q)
    jev = make(tmp_path, FakeTransport(), mode="replay")
    jev.ask("s", Q)
    assert jev.last["cost_usd"] == pytest.approx(0.00002) and jev.last["latency_s"] >= 0 and jev.last["replayed"]


def test_concurrent_live_calls_each_get_one_ledger_row(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    jev = make(tmp_path, lambda url, body, headers: ANSWER)
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(lambda i: jev.ask(f"s{i}", Q), range(40)))
    rows = list(csv.DictReader((tmp_path / "spend.csv").open()))
    assert len(rows) == 40 and jev.live_calls == 40
