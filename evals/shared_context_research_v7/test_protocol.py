from __future__ import annotations

from .protocol import (
    COHORTS,
    LATENCY_REDUCTION_GATE,
    TOKEN_REDUCTION_GATE,
    TRACK1_CASES,
)


def test_cross_family_cohorts_and_frozen_thresholds() -> None:
    assert {cohort.provider for cohort in COHORTS} == {"anthropic", "openai-codex"}
    assert {cohort.model for cohort in COHORTS} == {
        "claude-sonnet-4-6",
        "gpt-5.4",
    }
    assert TOKEN_REDUCTION_GATE == 0.15
    assert LATENCY_REDUCTION_GATE == 0.20


def test_all_records_control_requests_every_record() -> None:
    control = next(case for case in TRACK1_CASES if case["id"] == "all_records_control")
    assert control["requested_indexes"] == tuple(range(control["record_count"]))
