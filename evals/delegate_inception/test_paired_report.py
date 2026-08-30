"""Tests for paired outcome statistics."""

from evals.delegate_inception.paired_report import exact_mcnemar_p


def test_exact_mcnemar_no_discordance_is_uninformative():
    assert exact_mcnemar_p(0, 0) == 1.0


def test_exact_mcnemar_is_two_sided_and_symmetric():
    assert exact_mcnemar_p(0, 6) == exact_mcnemar_p(6, 0) == 0.03125
