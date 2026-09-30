"""Calibration fitted on our own labelled rows (train split), applied to held-out rows.

Raw model probabilities are not trusted: a confidence threshold decides which
answers are accepted, and histogram binning maps confidence to the accuracy
actually observed at that confidence.
"""


def fit_threshold(conf, correct, target):
    """Lowest threshold t such that rows with confidence >= t are at least `target` accurate; None if none."""
    best = None
    for t in sorted(set(conf), reverse=True):
        acc = [c for s, c in zip(conf, correct) if s >= t]
        if sum(acc) / len(acc) >= target:
            best = t
    return best


def selective(conf, correct, threshold):
    """(coverage, accuracy on accepted rows) at a confidence threshold."""
    kept = [c for s, c in zip(conf, correct) if threshold is not None and s >= threshold]
    return len(kept) / len(conf), (sum(kept) / len(kept) if kept else None)


def fit_binning(conf, correct, bins=5):
    acc = []
    for b in range(bins):
        idx = [i for i, s in enumerate(conf) if min(int(s * bins), bins - 1) == b]
        acc.append(sum(correct[i] for i in idx) / len(idx) if idx else None)
    overall = sum(correct) / len(correct)

    def calibrated(s):
        a = acc[min(int(s * bins), bins - 1)]
        return overall if a is None else a

    return calibrated
