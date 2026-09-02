"""Authoritative V2 schedule and protocol constants.

This module contains no model calls.  Its tables are frozen before the V2
preflight and are hashed into the V2 seal before any scored observation.
"""

from __future__ import annotations

from collections import Counter
from itertools import permutations
from typing import Iterable


TARGET_REVISION = "180291162ff4df0d42b5dc4fecd08005cf7cebf9"
MODEL = "claude-haiku-4-5"
PROVIDER = "claude-code"

PILOT_DEPENDENT = (
    "compact_release_map",
    "ordered_dependency_plan",
    "artifact_policy_join",
    "distractor_filtered_catalog",
)
EXPANSION_DEPENDENT = (
    "multi_key_reconciliation",
    "bounded_payload_edge",
)
DEPENDENT = PILOT_DEPENDENT + EXPANSION_DEPENDENT
CONTROLS = (
    "independent_local_control",
    "independent_detached_control",
)
PREFLIGHT_ONLY = (
    "preflight_detached_echo",
    "preflight_shared_echo",
)

ARM_ORDERS: dict[tuple[int, str], tuple[str, str, str]] = {
    (377, "preflight_detached_echo"): ("A", "B", "C"),
    (377, "preflight_shared_echo"): ("C", "A", "B"),
    (377, "distractor_filtered_catalog"): ("A", "C", "B"),
    (377, "compact_release_map"): ("B", "C", "A"),
    (377, "artifact_policy_join"): ("C", "A", "B"),
    (377, "ordered_dependency_plan"): ("A", "B", "C"),
    (377, "multi_key_reconciliation"): ("B", "A", "C"),
    (377, "bounded_payload_edge"): ("C", "B", "A"),
    (377, "independent_detached_control"): ("C", "A", "B"),
    (377, "independent_local_control"): ("B", "C", "A"),
    (378, "artifact_policy_join"): ("C", "B", "A"),
    (378, "compact_release_map"): ("A", "B", "C"),
    (378, "distractor_filtered_catalog"): ("C", "A", "B"),
    (378, "ordered_dependency_plan"): ("B", "C", "A"),
    (378, "multi_key_reconciliation"): ("B", "A", "C"),
    (378, "bounded_payload_edge"): ("A", "C", "B"),
    (378, "independent_detached_control"): ("C", "B", "A"),
    (378, "independent_local_control"): ("B", "A", "C"),
}

PILOT_EXECUTION_377 = (
    "independent_detached_control",
    "independent_local_control",
    "artifact_policy_join",
    "ordered_dependency_plan",
    "distractor_filtered_catalog",
    "compact_release_map",
)
EXPANSION_EXECUTION_377 = (
    "bounded_payload_edge",
    "multi_key_reconciliation",
)
CONFIRMATION_EXECUTION_378 = (
    "independent_local_control",
    "independent_detached_control",
    "bounded_payload_edge",
    "ordered_dependency_plan",
    "compact_release_map",
    "multi_key_reconciliation",
    "distractor_filtered_catalog",
    "artifact_policy_join",
)

DISABLED_CONSUMER_TOOLSETS = (
    "terminal",
    "code_execution",
    "delegation",
    "memory",
    "session_search",
)
ENABLED_CONSUMER_TOOLSETS = ("file",)
FORBIDDEN_CONSUMER_TOOLS = frozenset({
    "terminal",
    "process",
    "execute_code",
    "delegate_task",
    "memory",
    "session_search",
})
REQUIRED_CONSUMER_TOOLS = frozenset({
    "read_file",
    "write_file",
    "kanban_show",
    "kanban_complete",
})
ALLOWED_KANBAN_CALLS = frozenset({
    "kanban_show",
    "kanban_complete",
    "kanban_heartbeat",
})


def arm_order(task_id: str, seed: int) -> tuple[str, str, str]:
    try:
        return ARM_ORDERS[(seed, task_id)]
    except KeyError:
        raise KeyError(f"no frozen V2 order for {task_id}@{seed}") from None


def _position_counts(
    task_ids: Iterable[str], seed: int
) -> dict[str, tuple[int, int, int]]:
    orders = [arm_order(task_id, seed) for task_id in task_ids]
    return {
        arm: tuple(sum(order[index] == arm for order in orders) for index in range(3))
        for arm in "ABC"
    }


def validate_schedule() -> dict[str, object]:
    expected_permutations = {tuple(value) for value in permutations("ABC")}
    for seed in (377, 378):
        actual = {arm_order(task_id, seed) for task_id in DEPENDENT}
        if actual != expected_permutations:
            raise ValueError(f"dependent schedule is not a full block at seed {seed}")
    pilot_counts = _position_counts(PILOT_DEPENDENT, 377)
    if any(max(values) - min(values) > 1 for values in pilot_counts.values()):
        raise ValueError("pilot arm positions are not near-balanced")
    if Counter(PILOT_EXECUTION_377) != Counter(PILOT_DEPENDENT + CONTROLS):
        raise ValueError("pilot fixture execution table is incomplete")
    if Counter(EXPANSION_EXECUTION_377) != Counter(EXPANSION_DEPENDENT):
        raise ValueError("expansion fixture execution table is incomplete")
    if Counter(CONFIRMATION_EXECUTION_378) != Counter(DEPENDENT + CONTROLS):
        raise ValueError("confirmation fixture execution table is incomplete")
    if any(
        set(arm_order(task_id, 377)) != {"A", "B", "C"} for task_id in PREFLIGHT_ONLY
    ):
        raise ValueError("preflight order is not a complete arm permutation")
    return {
        "pilot_position_counts": pilot_counts,
        "dependent_full_block": True,
        "table_entries": len(ARM_ORDERS),
        "scored_table_entries": 16,
    }
