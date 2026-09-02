"""V3 treatment and lifecycle classification over the real V2 worker kernel."""

from __future__ import annotations

import base64
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
from typing import Any, Iterator

from evals.shared_context_research import runtime_v2
from evals.shared_context_research.runtime import (
    HANDOFF_CLOSE,
    HANDOFF_OPEN,
    RuntimeConfig,
)
from evals.shared_context_research.shared_context import canonical_bytes, digest_bytes
from evals.shared_context_research.tasks import WorkflowTask

from .protocol_v3 import ALLOWED_KANBAN_OPERATIONS


def _task_hash(task_id: str) -> str:
    return hashlib.sha256(task_id.encode("utf-8")).hexdigest()


def durable_projection_v3(
    task: WorkflowTask,
) -> tuple[str, list[dict[str, Any]], bool]:
    """Commit context to SQLite, close it, and read it from a fresh process."""

    workflow_id = f"{task.task_id}-v3"
    keys = list(task.reads)
    with tempfile.TemporaryDirectory(prefix="shared-context-v3-store-") as temp:
        database = Path(temp) / "context.sqlite3"
        conn = sqlite3.connect(database)
        try:
            conn.execute(
                "CREATE TABLE context_values ("
                "workflow_id TEXT NOT NULL, key TEXT NOT NULL, payload BLOB NOT NULL, "
                "sha256 TEXT NOT NULL, committed INTEGER NOT NULL, "
                "PRIMARY KEY (workflow_id, key))"
            )
            payloads: dict[str, bytes] = {}
            for key in keys:
                value = (
                    task.source[key]
                    if task.task_id == "multi_key_reconciliation"
                    else task.source
                )
                payload = canonical_bytes(value)
                payloads[key] = payload
                conn.execute(
                    "INSERT INTO context_values VALUES (?, ?, ?, ?, 0)",
                    (workflow_id, key, payload, digest_bytes(payload)),
                )
            conn.execute(
                "UPDATE context_values SET committed = 1 WHERE workflow_id = ?",
                (workflow_id,),
            )
            conn.commit()
        finally:
            conn.close()

        command = [
            sys.executable,
            "-m",
            "evals.shared_context_research_v3.durable_reader_v3",
            "--database",
            str(database),
            "--workflow",
            workflow_id,
            "--keys",
            *keys,
        ]
        run = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="strict",
        )
        encoded = json.loads(run.stdout)
        readbacks = {key: base64.b64decode(encoded[key]) for key in keys}

    if task.task_id == "multi_key_reconciliation":
        reconstructed = {
            key: json.loads(readbacks[key].decode("utf-8")) for key in keys
        }
        payload = canonical_bytes(reconstructed)
        text = "\n".join(
            f'<scratchpad key="{key}">{readbacks[key].decode("utf-8")}</scratchpad>'
            for key in keys
        )
        exact = reconstructed == task.source
    else:
        payload = readbacks["handoff"]
        text = HANDOFF_OPEN + payload.decode("utf-8") + HANDOFF_CLOSE
        exact = payload == canonical_bytes(task.source)
    receipts = [
        {
            "hop": f"durable_context:{key}",
            "byte_count": len(readbacks[key]),
            "sha256": digest_bytes(readbacks[key]),
            "fresh_process_read": True,
        }
        for key in keys
    ]
    receipts.append({
        # Keep the execution kernel's integrity hook while declaring the V3
        # transport explicitly.
        "hop": "scratchpad_readback",
        "transport": "sqlite_fresh_process",
        "byte_count": len(payload),
        "sha256": digest_bytes(payload),
        "fresh_process_read": True,
    })
    return text, receipts, exact


def reclassify_trace_v3(arm: dict[str, Any]) -> list[dict[str, str]]:
    """Allow an own-task terminal block but reject every foreign task target."""

    consumer = arm["consumer"]
    active = str(consumer["task_id"])
    calls = consumer.get("tool_trace") or []
    violations = [
        item
        for item in (arm.get("trace_scope") or {}).get("violations", [])
        if not (
            item.get("tool") == "kanban_block"
            and item.get("reason") == "forbidden_kanban_tool"
        )
    ]
    lifecycle: list[dict[str, str]] = []
    for call in calls:
        name = str(call.get("name") or "")
        if not name.startswith("kanban_"):
            continue
        arguments = call.get("arguments") or {}
        target = str(arguments.get("task_id") or active)
        relation = "own_active_task" if target == active else "foreign_task"
        if target != active:
            violations.append({"tool": name, "reason": "foreign_task_id"})
        if name not in ALLOWED_KANBAN_OPERATIONS:
            marker = {"tool": name, "reason": "forbidden_kanban_tool"}
            if marker not in violations:
                violations.append(marker)
        if name == "kanban_block":
            lifecycle.append({
                "operation": name,
                "target_relation": relation,
                "actor_task_id_sha256": _task_hash(active),
                "target_task_id_sha256": _task_hash(target),
            })
    trace_scope = arm.setdefault("trace_scope", {})
    trace_scope["violations"] = violations
    trace_scope["ok"] = not violations
    checks = arm.setdefault("consumer_checks", {})
    checks["trace_scope"] = not violations
    arm["scope_expansion"] = bool(arm.get("extra_files")) or bool(violations)
    arm["ok"] = all(bool(value) for value in checks.values())
    arm["false_success"] = not arm["ok"] and (
        consumer.get("status") == "done"
        or str(consumer.get("summary") or "").strip() == "consumer-complete"
    )
    return lifecycle


@contextmanager
def _v3_treatment() -> Iterator[None]:
    original = runtime_v2._scratchpad_projection
    runtime_v2._scratchpad_projection = durable_projection_v3
    try:
        yield
    finally:
        runtime_v2._scratchpad_projection = original


def run_fixture_v3(
    task: WorkflowTask,
    schedule_seed: int,
    config: RuntimeConfig,
    *,
    preflight: bool = False,
) -> dict[str, Any]:
    with _v3_treatment():
        record = runtime_v2.run_fixture_v2(
            task, schedule_seed, config, preflight=preflight
        )
    events: list[dict[str, str]] = []
    for arm_name, arm in record.get("arms", {}).items():
        for event in reclassify_trace_v3(arm):
            events.append({"arm": arm_name, **event})
    if record.get("arms"):
        record["integrity"]["all_trace_scopes"] = all(
            arm["trace_scope"]["ok"] for arm in record["arms"].values()
        )
    record["public_lifecycle_events"] = events
    return record
