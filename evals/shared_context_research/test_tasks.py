from __future__ import annotations

from .shared_context import canonical_bytes
from .tasks import PREFLIGHT_TASKS, TASKS, TASKS_BY_ID, build_tasks


def test_fixtures_are_deterministic_and_unique() -> None:
    assert build_tasks() == build_tasks()
    ids = [task.task_id for task in TASKS]
    assert len(ids) == len(set(ids)) == 8


def test_pilot_shape_and_controls() -> None:
    pilot = [task for task in TASKS if not task.expansion_only]
    assert len(pilot) == 6
    assert sum(task.dependent for task in pilot) == 4
    assert all(
        task.source is None and not task.reads for task in pilot if not task.dependent
    )


def test_preflight_fixtures_are_not_scored_cohort_members() -> None:
    assert {task.task_id for task in PREFLIGHT_TASKS} == {
        "preflight_detached_echo",
        "preflight_shared_echo",
    }
    assert not {task.task_id for task in PREFLIGHT_TASKS}.intersection(
        task.task_id for task in TASKS
    )
    assert len(TASKS_BY_ID) == len(TASKS) + len(PREFLIGHT_TASKS)


def test_bounded_payload_is_near_but_below_field_cap_before_wrapper() -> None:
    task = next(task for task in TASKS if task.task_id == "bounded_payload_edge")
    size = len(canonical_bytes(task.source))
    assert 3000 <= size < 4096
