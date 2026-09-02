"""Run the real B transport first, then the existing A/B/C kernel."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import shutil
import tempfile
from typing import Any, Iterator

from evals.shared_context_research import runtime_v2
from evals.shared_context_research.runtime import RuntimeConfig, _remove_tree, _run_card
from evals.shared_context_research.shared_context import canonical_bytes, digest_bytes
from evals.shared_context_research.tasks import read_json, write_json
from evals.shared_context_research_v3.runtime_v3 import run_fixture_v3

from .tasks_v5 import consumer_operation_v5


@contextmanager
def _v5_operation() -> Iterator[None]:
    original = runtime_v2.consumer_operation
    runtime_v2.consumer_operation = consumer_operation_v5
    try:
        yield
    finally:
        runtime_v2.consumer_operation = original


def run_b_gate_v5(task, config: RuntimeConfig) -> dict[str, Any]:
    """Exercise only the real detached Kanban projection and external oracle."""

    root = Path(tempfile.mkdtemp(prefix=f"shared-context-v5-b-{task.task_id}-"))
    conn = None
    try:
        environment = runtime_v2._make_environment(
            root, "B", config, include_producer=True
        )
        kb = runtime_v2._load_target(config)
        schema = runtime_v2._schema_receipt(environment, config)
        producer_workspace = environment.root / "producer-workspace"
        producer_workspace.mkdir(parents=True)
        write_json(producer_workspace / "source.json", task.source)
        with runtime_v2._activate_environment(environment, config):
            conn = kb.connect(board=environment.board)
            producer = _run_card(
                kb,
                conn,
                config=config,
                home=environment.home,
                board=environment.board,
                title=f"V5 produce {task.task_id}",
                body=runtime_v2._producer_body_v2(task),
                assignee="producer",
                workspace=producer_workspace,
            )
            conn = producer.pop("connection")
            conn.close()
            conn = None
        handoff = producer_workspace / "handoff.json"
        payload = handoff.read_bytes() if handoff.is_file() else b""
        expected = canonical_bytes(task.source)
        checks = {
            "status_done": producer["status"] == "done",
            "handoff_exact": handoff.is_file() and read_json(handoff) == task.source,
            "digest_exact": digest_bytes(payload) == digest_bytes(expected),
        }
        if not all(checks.values()):
            return {"task": task.task_id, "producer_checks": checks, "arm": None}
        summary = str(producer["summary"])
        common_tokens = runtime_v2._usage_total(producer)
        common_duration = float(producer["duration_seconds"])
        _remove_tree(producer_workspace)
        with _v5_operation():
            arm = runtime_v2._run_consumer(
                task,
                "B",
                config=config,
                environment=environment,
                kb=kb,
                producer=producer,
                producer_summary=summary,
                producer_payload=payload,
                shared_artifact=None,
                common_tokens=common_tokens,
                common_duration=common_duration,
            )
        return {
            "task": task.task_id,
            "producer_checks": checks,
            "producer_summary_chars": len(summary),
            "source_payload_chars": len(expected.decode("utf-8")),
            "schema_safe": schema["forbidden_absent"]
            and schema["required_present"]
            and schema["surface_bounded"],
            "arm": arm,
        }
    finally:
        if conn is not None:
            conn.close()
        shutil.rmtree(root, ignore_errors=True)


def run_comparison_v5(
    task, schedule_seed: int, config: RuntimeConfig
) -> dict[str, Any]:
    with _v5_operation():
        return run_fixture_v3(task, schedule_seed, config)
