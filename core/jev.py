"""Jev (TypeSafe System One) client over OpenRouter, with record/replay and a spend cap.

Every response is recorded under cache_dir by the sha256 of the request body, so
reruns replay offline. mode="replay" never calls the API; mode="record" calls it
only for requests with no recording. Each live call appends a row to the spend
ledger (CSV) and is refused once the ledger total reaches cap_usd.

The key comes from OPENROUTER_API_KEY in the environment or private/.env; it is
only ever sent in the Authorization header, never logged or recorded.
"""

import csv
import datetime as dt
import hashlib
import json
import os
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "https://openrouter.ai/api/v1/systemone"
MODEL = "typesafe/jev-1.13"  # pinned so calibrated thresholds stay valid
USD_PER_INPUT_TOKEN = 0.04 / 1_000_000  # measured 2026-09; output tokens are free
LEDGER_FIELDS = ["utc", "request", "input_tokens", "cost_usd", "estimated", "note"]
CAP_MARGIN_USD = 0.01  # stop this close to the cap: a batch in flight can overshoot by a few calls
RETRY_CODES = {408, 429, 500, 502, 503, 524, 529}


class MissingRecording(RuntimeError):
    pass


class SpendCapReached(RuntimeError):
    pass


class TransientError(RuntimeError):
    pass


def load_key(environ=os.environ, env_file=ROOT / "private" / ".env"):
    if environ.get("OPENROUTER_API_KEY"):
        return environ["OPENROUTER_API_KEY"]
    if Path(env_file).exists():
        for line in Path(env_file).read_text().splitlines():
            name, sep, value = line.strip().removeprefix("export ").partition("=")
            if sep and name.strip() == "OPENROUTER_API_KEY":
                return value.strip().strip("'\"")
    raise RuntimeError("OPENROUTER_API_KEY not set (environment or private/.env)")


def http_transport(url, body, headers, timeout=60):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        msg = f"Jev HTTP {e.code}: {e.read().decode(errors='replace')[:300]}"
        raise (TransientError if e.code in RETRY_CODES else RuntimeError)(msg) from None
    except (urllib.error.URLError, TimeoutError) as e:
        raise TransientError(f"Jev network error: {e}") from None


def ledger_total(path):
    if not Path(path).exists():
        return 0.0
    with Path(path).open() as f:
        return sum(float(r["cost_usd"]) for r in csv.DictReader(f))


class Jev:
    usd_in, usd_out = USD_PER_INPUT_TOKEN, 0.0  # fallback prices when the response has no usage.cost

    def __init__(self, key=None, mode="replay", model=MODEL, endpoint=ENDPOINT, transport=http_transport,
                 cache_dir=ROOT / "bench" / "recordings", ledger=ROOT / "bench" / "spend.csv", cap_usd=5.0,
                 retries=5, sleep=time.sleep, note=""):
        assert mode in ("replay", "record")
        self._key = key
        self.mode, self.model, self.endpoint, self.transport = mode, model, endpoint, transport
        self.cache_dir, self.ledger, self.cap_usd = Path(cache_dir), Path(ledger), cap_usd
        self.retries, self.sleep, self.note = retries, sleep, note
        self.live_calls = self.replayed = 0
        self.cost = 0.0
        self._lock = threading.Lock()  # ledger, counters and cap check are shared by worker threads
        self.last = {}  # latency_s, cost_usd, replayed of the most recent answer (live or recorded)

    def __repr__(self):
        return f"{type(self).__name__}(model={self.model!r}, mode={self.mode!r}, live_calls={self.live_calls}, cost={self.cost:.6f})"

    def _path(self, body):
        h = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        return h, self.cache_dir / h[:2] / f"{h}.json"

    def ask(self, state, questions):
        return self._post({"model": self.model, "state": state, "questions": questions})

    def _post(self, body):
        h, path = self._path(body)
        if path.exists():
            self.replayed += 1
            rec = json.loads(path.read_text())
            self._set_last(rec["response"], rec.get("latency_s", 0.0), True)
            return rec["response"]
        if self.mode == "replay":
            raise MissingRecording(f"no recording for request {h[:12]} (run with mode='record')")
        with self._lock:
            if ledger_total(self.ledger) >= self.cap_usd - CAP_MARGIN_USD:
                raise SpendCapReached(f"spend ledger {self.ledger} has reached the ${self.cap_usd} cap")
        if self._key is None:
            self._key = load_key()
        headers = {"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"}
        started = time.monotonic()
        for attempt in range(self.retries):
            try:
                out = self.transport(self.endpoint, body, headers)
                break
            except TransientError:
                if attempt == self.retries - 1:
                    raise
                self.sleep(min(2 ** attempt, 30))
        latency = time.monotonic() - started
        with self._lock:
            self._ledger_add(h, out.get("usage") or {})
            self.live_calls += 1
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"request": body, "response": out, "latency_s": round(latency, 3)},
                                   ensure_ascii=False, indent=1))
        self._set_last(out, latency, False)
        return out

    def _cost(self, usage):
        """(input tokens, cost in USD, estimated?) from a Jev or chat-completions usage block."""
        tin = int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0)
        tout = int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)
        if usage.get("cost") is not None:
            return tin, float(usage["cost"]), False
        return tin, tin * self.usd_in + tout * self.usd_out, True

    def _set_last(self, response, latency, replayed):
        cost = self._cost(response.get("usage") or {})[1]
        self.last = {"latency_s": latency, "cost_usd": cost, "replayed": replayed}

    def _ledger_add(self, request_hash, usage):
        tokens, cost, estimated = self._cost(usage)
        self.cost += cost
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        new = not self.ledger.exists()
        with self.ledger.open("a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=LEDGER_FIELDS)
            if new:
                w.writeheader()
            w.writerow({"utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                        "request": request_hash[:16], "input_tokens": tokens, "cost_usd": f"{cost:.8f}",
                        "estimated": int(estimated), "note": self.note})
