import pytest

from core.metrics import (accuracy, brier, confusion, ece, macro_f1, paired_bootstrap_diff, recall_at_k,
                          roc_auc)

Y = ["a", "a", "b", "b", "c"]
P = ["a", "b", "b", "b", "a"]


def test_accuracy_and_confusion():
    assert accuracy(Y, P) == pytest.approx(0.6)
    assert confusion(Y, P, labels=["a", "b", "c"]) == [[1, 1, 0], [0, 2, 0], [1, 0, 0]]


def test_macro_f1_averages_per_label_f1_including_zero_for_missed_label():
    # a: p=1/2 r=1/2 f=.5 ; b: p=2/3 r=1 f=.8 ; c: f=0
    assert macro_f1(Y, P, labels=["a", "b", "c"]) == pytest.approx((0.5 + 0.8 + 0) / 3)


def test_roc_auc_counts_ties_as_half():
    assert roc_auc([1, 1, 0, 0], [0.9, 0.5, 0.5, 0.1]) == pytest.approx((1 + 1 + 0.5 + 1) / 4)


def test_brier_is_mean_squared_error_of_the_probability_vector():
    probs = [{"a": 1.0, "b": 0.0}, {"a": 0.5, "b": 0.5}]
    assert brier(["a", "a"], probs) == pytest.approx((0 + (0.25 + 0.25)) / 2)


def test_ece_is_zero_for_perfectly_calibrated_confidence():
    # confidence 0.5 in a bin with 50% accuracy, 1.0 in a bin with 100% accuracy
    assert ece([0.5, 0.5, 1.0], [1, 0, 1], bins=10) == pytest.approx(0.0)
    assert ece([0.9, 0.9], [0, 0], bins=10) == pytest.approx(0.9)


def test_paired_bootstrap_ci_excludes_zero_when_one_arm_is_always_better():
    diff, lo, hi = paired_bootstrap_diff([1] * 40, [0] * 20 + [1] * 20, n=500, seed=1)
    assert diff == pytest.approx(0.5) and lo > 0 and hi <= 1


def test_recall_at_k_is_share_of_rows_whose_gold_clause_is_in_the_top_k():
    assert recall_at_k([["x", "y"], ["z", "x"]], [{"y"}, {"q"}], k=2) == pytest.approx(0.5)
    assert recall_at_k([["x", "y"]], [{"y"}], k=1) == 0.0


def test_bootstrap_of_an_empty_split_is_nan_not_a_crash():
    import math
    from core.metrics import bootstrap_ci
    assert all(math.isnan(v) for v in bootstrap_ci([]))


def test_confusion_counts_predictions_outside_the_labels_in_an_extra_column():
    assert confusion(["a", "b"], ["a", "unparsed"], labels=["a", "b"]) == [[1, 0, 0], [0, 0, 1]]
