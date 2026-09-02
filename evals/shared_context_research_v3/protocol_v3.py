"""Frozen constants for the prospectively published V3 repetition."""

from __future__ import annotations

from dataclasses import dataclass

from evals.shared_context_research.protocol_v2 import (
    PILOT_DEPENDENT,
    PILOT_EXECUTION_377,
)


TARGET_REVISION = "c5c9aa8d44e03f4e8b5fe7f230cfd97ab2dde0bf"
PROVIDER = "claude-code"
DEPENDENT = PILOT_DEPENDENT
CONTROLS = ("independent_detached_control", "independent_local_control")
TASKS = tuple(PILOT_EXECUTION_377)


@dataclass(frozen=True)
class Cohort:
    id: str
    model: str
    seed: int


COHORTS = (
    Cohort("haiku-s377", "claude-haiku-4-5", 377),
    Cohort("haiku-s378", "claude-haiku-4-5", 378),
    Cohort("sonnet-s377", "claude-sonnet-4-6", 377),
)

ALLOWED_KANBAN_OPERATIONS = frozenset({
    "kanban_show",
    "kanban_complete",
    "kanban_heartbeat",
    "kanban_block",
})


def validate_protocol_v3() -> None:
    assert len({cohort.id for cohort in COHORTS}) == len(COHORTS)
    assert {cohort.model for cohort in COHORTS} == {
        "claude-haiku-4-5",
        "claude-sonnet-4-6",
    }
    assert set(TASKS) == set(DEPENDENT) | set(CONTROLS)
