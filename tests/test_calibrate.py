import pytest

from core.calibrate import fit_binning, fit_threshold, selective


def test_threshold_is_lowest_confidence_whose_accepted_rows_reach_the_target_accuracy():
    conf = [0.95, 0.9, 0.8, 0.7, 0.6, 0.5]
    correct = [1, 1, 1, 0, 1, 0]
    assert fit_threshold(conf, correct, target=0.9) == 0.8
    assert fit_threshold(conf, correct, target=1.01) is None


def test_selective_reports_coverage_and_accuracy_of_accepted_rows():
    assert selective([0.9, 0.8, 0.2, 0.1], [1, 0, 1, 1], threshold=0.5) == pytest.approx((0.5, 0.5))
    assert selective([0.1], [1], threshold=0.5) == (0.0, None)


def test_binning_maps_confidence_to_the_accuracy_seen_in_its_bin_on_train():
    cal = fit_binning([0.95, 0.92, 0.3, 0.35], [1, 0, 1, 1], bins=2)
    assert cal(0.99) == pytest.approx(0.5) and cal(0.1) == pytest.approx(1.0)
