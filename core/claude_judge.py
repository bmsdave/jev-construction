"""Claude as judge (arm D) over OpenRouter chat completions.

Same recording, replay, spend cap and ledger as the Jev client. Claude is asked
for one label and a probability per label as JSON; anything else is kept as
"unparsed" (counted wrong), never guessed.
"""

import json
import re

from core.jev import Jev

CHAT_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
CLAUDE_MODEL = "anthropic/claude-opus-5.5"
SYSTEM = """You are an experienced UK building control surveyor. Answer the question about the work item
in the JSON state. Choose exactly one label:
{labels}
Reply with JSON only: {{"label": "<one label>", "probabilities": {{"<label>": <0..1>, ...}}}} with a
probability for every label, summing to 1."""


class TruncatedAnswer(RuntimeError):
    pass


class ClaudeJudge(Jev):
    usd_in, usd_out = 4.0 / 1_000_000, 20.0 / 1_000_000  # OpenRouter price for claude-opus-5.5, 2026-09-29

    def __init__(self, model=CLAUDE_MODEL, endpoint=CHAT_ENDPOINT, max_tokens=300, retries=8, reasoning=False, **kw):
        # retries: new OpenRouter accounts get 20 requests/minute on Opus, so 429s need patient backoff
        super().__init__(model=model, endpoint=endpoint, retries=retries, **kw)
        self.max_tokens, self.reasoning = max_tokens, reasoning

    def judge(self, state, question, labels):
        system = SYSTEM.format(labels="\n".join(f"- {k}: {v}" for k, v in labels.items()))
        body = {"model": self.model, "max_tokens": self.max_tokens, "temperature": 0,
                "reasoning": {"enabled": self.reasoning},
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": f"{question}\n\n{json.dumps(state, ensure_ascii=False)}"}]}
        choice = self._post(body)["choices"][0]
        text = choice["message"]["content"] or ""
        if choice.get("finish_reason") == "length" and not text.strip():
            raise TruncatedAnswer(f"no answer within max_tokens={self.max_tokens} (reasoning used the budget?)")
        return parse(text, labels)


def parse(text, labels):
    m = re.search(r"\{.*\}", text, re.S)
    try:
        d = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        d = {}
    if d.get("label") not in labels:
        return {"label": "unparsed", "probs": {k: 1 / len(labels) for k in labels}, "confidence": 0.0}
    raw = {k: float((d.get("probabilities") or {}).get(k, 0.0)) for k in labels}
    total = sum(raw.values()) or 1.0
    probs = {k: v / total for k, v in raw.items()}
    return {"label": d["label"], "probs": probs, "confidence": max(probs.values())}
