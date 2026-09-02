from __future__ import annotations

from typing import Any

from .analysis_v2 import final_verdict_v2, pilot_expansion_gate_v2
from .protocol_v2 import CONTROLS, DEPENDENT, PILOT_DEPENDENT


def _arm(
    *,
    ok: bool = True,
    fidelity: bool = True,
    tokens: int | None = 100,
    duration: float | None = 10.0,
    false_success: bool = False,
) -> dict[str, Any]:
    return {
        "ok": ok,
        "handoff_fidelity": fidelity,
        "total_tokens": tokens,
        "duration_seconds": duration,
        "false_success": false_success,
    }


def _fixture(
    task: str,
    seed: int,
    *,
    dependent: bool = True,
    a: dict[str, Any] | None = None,
    b: dict[str, Any] | None = None,
    c: dict[str, Any] | None = None,
    integrity: bool = True,
) -> dict[str, Any]:
    return {
        "task": task,
        "schedule_seed": seed,
        "dependent": dependent,
        "producer_admitted": True,
        "provider_failure": None,
        "integrity": {"all": integrity},
        "arms": {"A": a or _arm(), "B": b or _arm(), "C": c or _arm()},
    }


def _pilot_controls(seed: int = 377) -> list[dict[str, Any]]:
    return [_fixture(task, seed, dependent=False) for task in CONTROLS]


def test_pilot_stops_when_c_has_no_incremental_gain() -> None:
    rows = [
        _fixture(task, 377, b=_arm(tokens=100), c=_arm(tokens=95))
        for task in PILOT_DEPENDENT
    ] + _pilot_controls()
    gate = pilot_expansion_gate_v2(rows)
    assert gate["complete"] is True
    assert gate["expand"] is False
    assert gate["median_token_improvement_pct"] == 5.0
    assert final_verdict_v2(rows, expanded=False)["verdict"] == "NO OPPORTUNITY"


def test_c_only_correctness_opens_pilot_gate() -> None:
    rows = [_fixture(task, 377) for task in PILOT_DEPENDENT] + _pilot_controls()
    rows[0]["arms"]["B"] = _arm(ok=False)
    gate = pilot_expansion_gate_v2(rows)
    assert gate["complete"] is True
    assert gate["expand"] is True
    assert gate["triggers"]["correctness"] is True


def test_missing_usage_cannot_open_resource_gate() -> None:
    rows = [
        _fixture(task, 377, b=_arm(tokens=None), c=_arm(tokens=None))
        for task in PILOT_DEPENDENT
    ] + _pilot_controls()
    gate = pilot_expansion_gate_v2(rows)
    assert gate["complete"] is True
    assert gate["resource_gate_available"] is False
    assert gate["triggers"]["tokens"] is False
    assert gate["triggers"]["latency"] is False


def test_invalid_common_pair_makes_pilot_inconclusive() -> None:
    rows = [_fixture(task, 377) for task in PILOT_DEPENDENT] + _pilot_controls()
    rows[2]["integrity"]["all"] = False
    gate = pilot_expansion_gate_v2(rows)
    assert gate["complete"] is False
    assert gate["reason"] == "invalid_common_producer_pair_or_integrity"


def test_confirmation_requires_an_open_pilot_gate() -> None:
    rows = [_fixture(task, seed) for seed in (377, 378) for task in DEPENDENT] + [
        _fixture(task, seed, dependent=False)
        for seed in (377, 378)
        for task in CONTROLS
    ]
    decision = final_verdict_v2(rows, expanded=True)
    assert decision["verdict"] == "INCONCLUSIVE"
    assert decision["reason"] == "confirmation_without_open_pilot_gate"


def test_negative_confirmation_can_find_existing_handoff_sufficient() -> None:
    rows = [_fixture(task, seed) for seed in (377, 378) for task in DEPENDENT] + [
        _fixture(task, seed, dependent=False)
        for seed in (377, 378)
        for task in CONTROLS
    ]
    # A fidelity-only pilot opportunity opens confirmation, but task outcomes
    # and resources remain matched across the full cohort.
    pilot = next(
        row
        for row in rows
        if row["task"] == PILOT_DEPENDENT[0] and row["schedule_seed"] == 377
    )
    pilot["arms"]["B"]["handoff_fidelity"] = False
    decision = final_verdict_v2(rows, expanded=True)
    assert decision["gate"]["expand"] is True
    assert decision["verdict"] == "EXISTING HANDOFF SUFFICIENT"
