"""Read the durable outcome emitted by a real Hermes Kanban worker."""

from __future__ import annotations

from dataclasses import dataclass

from hermes_cli import kanban_db as kb


@dataclass(frozen=True)
class WorkerOutcome:
    text: str
    source: str
    task_status: str


def read_worker_outcome(task_id: str) -> WorkerOutcome:
    with kb.connect_closing() as conn:
        task = kb.get_task(conn, task_id)
        run = kb.latest_run(conn, task_id)
    if task is None:
        return WorkerOutcome("", "missing_task", "missing")
    if task.result and task.result.strip():
        return WorkerOutcome(task.result, "task.result", task.status)
    summary = str(getattr(run, "summary", "") or "")
    if summary.strip():
        return WorkerOutcome(summary, "latest_run.summary", task.status)
    return WorkerOutcome("", "missing_terminal_outcome", task.status)
