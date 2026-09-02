from __future__ import annotations

from .protocol_v2 import (
    ARM_ORDERS,
    DEPENDENT,
    PILOT_DEPENDENT,
    arm_order,
    validate_schedule,
)


def test_v2_schedule_is_complete_balanced_and_frozen() -> None:
    receipt = validate_schedule()
    assert receipt["dependent_full_block"] is True
    assert receipt["table_entries"] == 18
    assert receipt["scored_table_entries"] == 16
    assert set(receipt["pilot_position_counts"]) == {"A", "B", "C"}
    assert len(ARM_ORDERS) == 18
    for seed in (377, 378):
        assert all(set(arm_order(task, seed)) == {"A", "B", "C"} for task in DEPENDENT)


def test_pilot_positions_differ_by_at_most_one() -> None:
    for arm in "ABC":
        counts = [
            sum(arm_order(task, 377)[position] == arm for task in PILOT_DEPENDENT)
            for position in range(3)
        ]
        assert max(counts) - min(counts) <= 1
