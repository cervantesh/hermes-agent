from __future__ import annotations

from .analysis import PILOT_DEPENDENT, pilot_expansion_gate


def _row(
    task: str, arm: str, *, ok: bool = True, tokens: int = 100, duration: float = 10
) -> dict:
    return {
        "task": task,
        "arm": arm,
        "schedule_seed": 377,
        "ok": ok,
        "handoff_fidelity": True,
        "total_tokens": tokens,
        "duration_seconds": duration,
        "producer": {"checks": {"valid": True}},
    }


def test_no_expansion_at_ceiling_without_resource_gain() -> None:
    rows = [_row(task, arm) for task in PILOT_DEPENDENT for arm in "ABC"]
    result = pilot_expansion_gate(rows)
    assert result["complete"]
    assert not result["expand"]


def test_correctness_opportunity_opens_gate() -> None:
    rows = [_row(task, arm) for task in PILOT_DEPENDENT for arm in "ABC"]
    next(
        row for row in rows if row["task"] == PILOT_DEPENDENT[0] and row["arm"] == "B"
    )["ok"] = False
    assert pilot_expansion_gate(rows)["triggers"]["correctness"]


def test_inclusive_token_threshold_opens_gate() -> None:
    rows = []
    for task in PILOT_DEPENDENT:
        rows.extend([
            _row(task, "A"),
            _row(task, "B", tokens=100),
            _row(task, "C", tokens=85),
        ])
    assert pilot_expansion_gate(rows)["triggers"]["tokens"]


def test_invalid_producer_invalidates_the_paired_fixture() -> None:
    rows = [_row(task, arm) for task in PILOT_DEPENDENT for arm in "ABC"]
    rows[0]["producer"]["checks"]["valid"] = False
    result = pilot_expansion_gate(rows)
    assert not result["complete"]
    assert result["reason"] == "producer_validation_invalidated_pairs"
