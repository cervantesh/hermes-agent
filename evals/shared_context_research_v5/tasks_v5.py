"""Deterministic fixtures straddling the Kanban parent-summary cap."""

from __future__ import annotations

from dataclasses import replace
import random

from evals.shared_context_research.tasks import WorkflowTask


def _payload_task(task_id: str, *, count: int, seed: int) -> WorkflowTask:
    rng = random.Random(seed)
    records = [
        {
            "id": f"p{index:03d}",
            "opaque": f"value-{rng.getrandbits(160):040x}",
        }
        for index in range(count)
    ]
    selected_id = records[-1]["id"]
    return WorkflowTask(
        task_id=task_id,
        topology="detached_source",
        dependent=True,
        source={"records": records},
        consumer_local={"select": [selected_id]},
        expected={"selected": [records[-1]]},
        reads=("handoff",),
    )


def build_tasks_v5(seed: int = 377) -> tuple[WorkflowTask, WorkflowTask]:
    below = _payload_task("cap_below_control", count=50, seed=seed)
    above = _payload_task("cap_above_tail_dependency", count=82, seed=seed)
    return below, above


def consumer_operation_v5(task: WorkflowTask) -> str:
    if task.task_id not in {"cap_below_control", "cap_above_tail_dependency"}:
        raise KeyError(task.task_id)
    return (
        "Use the select list in consumer_input.json and emit the corresponding "
        "complete handoff records under `selected`, preserving select-list order."
    )


def task_for_seed(task_id: str, seed: int) -> WorkflowTask:
    by_id = {task.task_id: task for task in build_tasks_v5(seed)}
    # Return a distinct immutable instance so callers cannot accidentally share
    # fixture identity across processes.
    return replace(by_id[task_id])
