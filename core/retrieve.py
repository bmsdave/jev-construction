"""BM25 (Okapi) retrieval over clauses. Stdlib only; embeddings only if BM25 is measurably worse."""

import math
import re
from collections import Counter

STOP = set("""a an and are as at be by for from has have in into is it its of on or that the this to was were
will with which where when who not no any all other than such shall should may must""".split())


def _stem(w):
    """Crude suffix strip, enough to match replace/replacement, socket/sockets, add/adding."""
    for suf in ("ment", "ing", "ed", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3 and not w.endswith("ss"):
            return w[: -len(suf)]
    return w


def tokens(text):
    out = []
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        if w in STOP:
            continue
        out.append(_stem(w))
    return out


class BM25:
    def __init__(self, clauses, k1=1.2, b=0.75, text=lambda c: f"{c.ref} {c.text}"):
        self.clauses, self.k1, self.b = list(clauses), k1, b
        self.docs = [Counter(tokens(text(c))) for c in self.clauses]
        self.lens = [sum(d.values()) for d in self.docs]
        self.avg = sum(self.lens) / max(len(self.lens), 1)
        df = Counter(t for d in self.docs for t in d)
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def score(self, query_tokens, i):
        d, s = self.docs[i], 0.0
        for t in query_tokens:
            if t in d:
                tf = d[t]
                s += self.idf[t] * tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * self.lens[i] / self.avg))
        return s

    def search(self, query, k=5):
        q = tokens(query)
        scored = [(self.clauses[i], self.score(q, i)) for i in range(len(self.clauses))]
        scored = [x for x in scored if x[1] > 0]
        scored.sort(key=lambda x: -x[1])
        return scored[:k]
