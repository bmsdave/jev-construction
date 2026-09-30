"""Benchmark metrics, stdlib only."""

import random


def accuracy(y, p):
    return sum(a == b for a, b in zip(y, p)) / len(y)


def confusion(y, p, labels):
    """Rows = truth, columns = prediction; an extra last column counts predictions outside `labels`."""
    idx = {l: i for i, l in enumerate(labels)}
    other = any(b not in idx for b in p)
    m = [[0] * (len(labels) + other) for _ in labels]
    for a, b in zip(y, p):
        m[idx[a]][idx.get(b, len(labels))] += 1
    return m


def macro_f1(y, p, labels):
    f1s = []
    for l in labels:
        tp = sum(a == l and b == l for a, b in zip(y, p))
        fp = sum(a != l and b == l for a, b in zip(y, p))
        fn = sum(a == l and b != l for a, b in zip(y, p))
        f1s.append(2 * tp / (2 * tp + fp + fn) if tp else 0.0)
    return sum(f1s) / len(f1s)


def roc_auc(y01, scores):
    pos = [s for t, s in zip(y01, scores) if t]
    neg = [s for t, s in zip(y01, scores) if not t]
    if not pos or not neg:
        return float("nan")
    wins = sum(1.0 if a > b else 0.5 if a == b else 0.0 for a in pos for b in neg)
    return wins / (len(pos) * len(neg))


def brier(y, probs):
    """Multi-class Brier score: mean over rows of the summed squared error of the probability vector."""
    total = 0.0
    for label, pr in zip(y, probs):
        total += sum((pr.get(k, 0.0) - (k == label)) ** 2 for k in set(pr) | {label})
    return total / len(y)


def ece(confidences, correct, bins=10):
    """Expected calibration error of top-label confidence (equal-width bins)."""
    n, total = len(confidences), 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        idx = [i for i, c in enumerate(confidences) if lo < c <= hi or (b == 0 and c == 0)]
        if idx:
            conf = sum(confidences[i] for i in idx) / len(idx)
            acc = sum(correct[i] for i in idx) / len(idx)
            total += len(idx) / n * abs(conf - acc)
    return total


def bootstrap_ci(values, stat=lambda v: sum(v) / len(v), n=2000, seed=0, alpha=0.05):
    if not values:
        return float("nan"), float("nan"), float("nan")
    rng = random.Random(seed)
    stats = sorted(stat([values[rng.randrange(len(values))] for _ in values]) for _ in range(n))
    return stat(values), stats[int(alpha / 2 * n)], stats[int((1 - alpha / 2) * n) - 1]


def paired_bootstrap_diff(correct_a, correct_b, n=2000, seed=0, alpha=0.05):
    """Mean(correct_a - correct_b) with a paired bootstrap CI over the same rows."""
    return bootstrap_ci([a - b for a, b in zip(correct_a, correct_b)], n=n, seed=seed, alpha=alpha)


def recall_at_k(ranked_ids, gold_sets, k):
    return sum(bool(set(r[:k]) & g) for r, g in zip(ranked_ids, gold_sets)) / len(gold_sets)
