import pytest

from evals.issue_375_fidelity_research.analysis import analyze_wins


def test_exact_paired_analysis_matches_scipy_reference():
    result = analyze_wins(original_wins=75, ablated_wins=25, draws=0)

    assert result.non_draw_pairs == 100
    assert result.original_rate == 0.75
    assert result.two_sided_p_value == pytest.approx(5.636282034205402e-07)
    assert result.confidence_low == pytest.approx(0.6534475042411918)
    assert result.confidence_high == pytest.approx(0.8312202619003402)
    assert result.disposition == "DIRECTIONALLY_COMPATIBLE"


def test_draws_are_excluded_from_sign_test_but_retained_in_report():
    result = analyze_wins(original_wins=5, ablated_wins=5, draws=90)

    assert result.total_pairs == 100
    assert result.non_draw_pairs == 10
    assert result.draws == 90
    assert result.two_sided_p_value == 1.0
    assert result.disposition == "NON_CONFIRMATORY"


def test_zero_non_draw_pairs_are_nonconfirmatory_without_fake_rate():
    result = analyze_wins(original_wins=0, ablated_wins=0, draws=100)

    assert result.original_rate is None
    assert result.confidence_low is None
    assert result.confidence_high is None
    assert result.two_sided_p_value is None
    assert result.disposition == "NON_CONFIRMATORY"
