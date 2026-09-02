"""Common-producer real-worker runtime for the V2 experiment."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import tempfile
import time
from typing import Any, Iterator

from .protocol_v2 import (
    ALLOWED_KANBAN_CALLS,
    DISABLED_CONSUMER_TOOLSETS,
    ENABLED_CONSUMER_TOOLSETS,
    FORBIDDEN_CONSUMER_TOOLS,
    REQUIRED_CONSUMER_TOOLS,
    TARGET_REVISION,
    arm_order,
)
from .runtime import (
    HANDOFF_CLOSE,
    HANDOFF_OPEN,
    RuntimeConfig,
    _json_block,
    _load_target,
    _provider_failure,
    _remove_tree,
    _run_card,
    _session_details,
    _tree_files,
    _wait_worker_exit,
    _worker_log,
)
from .shared_context import WorkflowContextStore, canonical_bytes, digest_bytes
from .tasks import WorkflowTask, consumer_operation, read_json, write_json


PROTOCOL_TARGET = TARGET_REVISION
FILE_TOOLS = frozenset({"read_file", "write_file", "patch", "search_files"})


def _profile_config(max_iterations: int) -> bytes:
    disabled = "\n".join(f"    - {name}" for name in DISABLED_CONSUMER_TOOLSETS)
    return (
        "platform_toolsets:\n"
        "  cli:\n"
        "    - file\n"
        "agent:\n"
        f"  max_turns: {max_iterations}\n"
        "  disabled_toolsets:\n"
        f"{disabled}\n"
    ).encode("utf-8")


@dataclass(frozen=True)
class EvalEnvironment:
    arm: str
    root: Path
    home: Path
    database: Path
    workspaces_root: Path
    board: str
    consumer_workspace: Path
    config_sha256: str


def _make_environment(
    fixture_root: Path,
    arm: str,
    config: RuntimeConfig,
    *,
    include_producer: bool = False,
) -> EvalEnvironment:
    root = fixture_root / f"arm-{arm.lower()}"
    home = root / "home"
    workspaces = root / "board-workspaces"
    consumer_workspace = root / "consumer-workspace"
    home.mkdir(parents=True)
    workspaces.mkdir(parents=True)
    payload = _profile_config(config.max_iterations)
    (home / "config.yaml").write_bytes(payload)
    profiles = ["consumer"] + (["producer"] if include_producer else [])
    for profile in profiles:
        profile_root = home / "profiles" / profile
        profile_root.mkdir(parents=True)
        (profile_root / "config.yaml").write_bytes(payload)
    return EvalEnvironment(
        arm=arm,
        root=root,
        home=home,
        database=root / "kanban.db",
        workspaces_root=workspaces,
        board="shared-context-eval-v2",
        consumer_workspace=consumer_workspace,
        config_sha256=hashlib.sha256(payload).hexdigest(),
    )


@contextmanager
def _activate_environment(
    environment: EvalEnvironment,
    config: RuntimeConfig,
    *,
    profile: str | None = None,
    workspace: Path | None = None,
    kanban_task: str | None = None,
) -> Iterator[None]:
    home = environment.home / "profiles" / profile if profile else environment.home
    updates = {
        "HERMES_HOME": str(home),
        "HERMES_KANBAN_DB": str(environment.database),
        "HERMES_KANBAN_WORKSPACES_ROOT": str(environment.workspaces_root),
        "HERMES_KANBAN_BOARD": environment.board,
        "HERMES_MAX_ITERATIONS": str(config.max_iterations),
        "PYTHONPATH": str(config.repo_root),
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        "PATH": str(config.python_executable.parent)
        + os.pathsep
        + os.environ.get("PATH", ""),
    }
    if workspace is not None:
        updates["TERMINAL_CWD"] = str(workspace)
    if kanban_task is not None:
        updates["HERMES_KANBAN_TASK"] = kanban_task
    old = dict(os.environ)
    os.environ.update(updates)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(old)


def _schema_receipt(
    environment: EvalEnvironment, config: RuntimeConfig
) -> dict[str, Any]:
    with _activate_environment(
        environment,
        config,
        profile="consumer",
        workspace=environment.consumer_workspace,
        kanban_task="schema-probe",
    ):
        from model_tools import _clear_tool_defs_cache, get_tool_definitions

        _clear_tool_defs_cache()
        definitions = get_tool_definitions(
            enabled_toolsets=list(ENABLED_CONSUMER_TOOLSETS),
            disabled_toolsets=list(DISABLED_CONSUMER_TOOLSETS),
            quiet_mode=True,
        )
    normalized = sorted(definitions, key=lambda item: item["function"]["name"])
    names = {item["function"]["name"] for item in normalized}
    return {
        "profile": "consumer",
        "provider_override": (
            "anthropic" if config.provider == "claude-code" else config.provider
        ),
        "model_override": config.model,
        "max_iterations": config.max_iterations,
        "config_sha256": environment.config_sha256,
        "schema_sha256": digest_bytes(canonical_bytes(normalized)),
        "tool_names": sorted(names),
        "forbidden_absent": not bool(names & FORBIDDEN_CONSUMER_TOOLS),
        "required_present": REQUIRED_CONSUMER_TOOLS <= names,
        "surface_bounded": all(
            name in FILE_TOOLS or name.startswith("kanban_") for name in names
        ),
    }


def _profile_session_count(environment: EvalEnvironment) -> int:
    path = environment.home / "profiles" / "consumer" / "state.db"
    if not path.is_file():
        return 0
    conn = sqlite3.connect(path)
    try:
        table = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'sessions'"
        ).fetchone()
        if table is None:
            return 0
        return int(conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0])
    finally:
        conn.close()


def _single_consumer_session_id(environment: EvalEnvironment) -> str:
    """Resolve the sole fresh-profile session when lifecycle metadata omits it."""

    path = environment.home / "profiles" / "consumer" / "state.db"
    if not path.is_file():
        return ""
    conn = sqlite3.connect(path)
    try:
        table = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'sessions'"
        ).fetchone()
        if table is None:
            return ""
        rows = conn.execute("SELECT id FROM sessions ORDER BY id").fetchall()
        return str(rows[0][0]) if len(rows) == 1 else ""
    finally:
        conn.close()


def _task_count(kb, environment: EvalEnvironment, config: RuntimeConfig) -> int:
    with _activate_environment(environment, config):
        conn = kb.connect(board=environment.board)
        try:
            return int(conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0])
        finally:
            conn.close()


def _show_response_state(response: str) -> tuple[bool, bool]:
    """Return (found, not_found) without depending on error message spacing."""

    try:
        payload = json.loads(response)
    except (TypeError, json.JSONDecodeError):
        payload = {}
    error = str(payload.get("error") or "").lower()
    not_found = error.endswith(" not found")
    return not error and not not_found, not_found


def _show_probe(
    environment: EvalEnvironment,
    config: RuntimeConfig,
    producer_id: str,
) -> dict[str, Any]:
    with _activate_environment(
        environment,
        config,
        profile="consumer",
        workspace=environment.consumer_workspace,
        kanban_task="sentinel-probe",
    ):
        from tools.kanban_tools import _handle_show

        response = _handle_show({"task_id": producer_id})
    found, not_found = _show_response_state(response)
    return {
        "producer_id_sha256": digest_bytes(producer_id.encode("utf-8")),
        "found": found,
        "not_found": not_found,
    }


def _producer_body_v2(task: WorkflowTask) -> str:
    payload = canonical_bytes(task.source)
    digest = digest_bytes(payload)
    return (
        "Call kanban_show() first. Read source.json and create handoff.json with "
        "exactly the same canonical JSON value. Do not add or remove fields. "
        "Use file tools only; terminal and code execution are unavailable. "
        "Then call kanban_complete. Its summary must be exactly the delimited "
        f"block below, with no surrounding prose:\n{_json_block(task.source)}\n"
        "Its metadata must contain exactly these research fields (the tool may "
        "add its own lifecycle fields): "
        f'{{"byte_count":{len(payload)},"sha256":"{digest}"}}. '
        "Do not pass an artifacts list and do not create any other workspace file."
    )


def _parent_relay_v2(config: RuntimeConfig, block: str) -> dict[str, Any]:
    """Run the lossless relay while retaining Hermes's real usage fields."""

    from run_agent import AIAgent

    if config.provider == "claude-code":
        kwargs = {
            "provider": "anthropic",
            "model": config.model,
            "api_key": None,
            "api_mode": "anthropic_messages",
        }
    else:
        key = os.environ.get(f"{config.provider.upper()}_API_KEY")
        kwargs = {
            "provider": config.provider,
            "model": config.model,
            "api_key": key,
        }
    agent = AIAgent(
        quiet_mode=True,
        skip_context_files=True,
        skip_memory=True,
        enabled_toolsets=[],
        max_iterations=3,
        platform="cli",
        **kwargs,
    )
    try:
        result = agent.run_conversation(
            "Reproduce the delimited handoff block byte-for-byte and return only "
            f"that block. Do not interpret or summarize it.\n\n{block}",
            system_message=(
                "You are a lossless relay in a controlled experiment. Return the "
                "provided <handoff-json> block exactly and nothing else."
            ),
        )
    finally:
        agent.close()
    usage_keys = (
        "input_tokens",
        "output_tokens",
        "cache_read_tokens",
        "cache_write_tokens",
        "reasoning_tokens",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
    )
    tokens = {
        key: int(result[key]) for key in usage_keys if isinstance(result.get(key), int)
    }
    return {
        "text": str(result.get("final_response") or ""),
        "tokens": tokens,
        "api_calls": int(result.get("api_calls") or 0),
    }


def _consumer_body_v2(
    task: WorkflowTask,
    arm: str,
    handoff_text: str | None,
    shared_artifact: Path | None,
) -> str:
    if not task.dependent:
        source = "There is no upstream dependency. Do not look for handoff state."
    elif arm == "B" and task.topology == "shared_storage":
        source = (
            "Read the upstream value from this exact shared artifact path: "
            f"{shared_artifact}. Do not modify that file."
        )
    elif arm == "B":
        source = (
            "Use the canonical handoff block under `## Parent task results` in "
            "the output of kanban_show()."
        )
    else:
        source = (
            "Use only the following treatment handoff; do not search for other "
            f"workflow state:\n{handoff_text or ''}"
        )
    return (
        "Call kanban_show() first. "
        + source
        + " Read consumer_input.json. "
        + consumer_operation(task)
        + " Use file tools only; terminal, code execution, delegation, memory, "
        "and session search are unavailable. Do not inspect, search, read, or "
        "write any parent directory: every file target must remain inside your "
        "assigned workspace, except for the one exact read-only shared artifact "
        "path explicitly declared above when present. Write result.json as "
        "canonical or pretty JSON containing exactly the requested keys and "
        "values. Then call "
        "kanban_complete with summary exactly consumer-complete and metadata "
        "containing exactly the fields "
        + f'{{"arm":"{arm}","task":"{task.task_id}"}}. '
        "Do not pass an artifacts list and do not create any other workspace file."
    )


def _run_card_with_preview(
    kb,
    conn,
    *,
    config: RuntimeConfig,
    environment: EvalEnvironment,
    title: str,
    body: str,
    parents: tuple[str, ...],
) -> tuple[dict[str, Any], str]:
    workspace = environment.consumer_workspace
    workspace.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    task_id = kb.create_task(
        conn,
        title=title,
        body=body,
        assignee="consumer",
        created_by="shared-context-research-v2",
        workspace_kind="dir",
        workspace_path=str(workspace),
        parents=parents,
        max_runtime_seconds=config.timeout_seconds,
        model_override=config.model,
        provider_override=(
            "anthropic" if config.provider == "claude-code" else config.provider
        ),
        board=environment.board,
    )
    preview = kb.build_worker_context(conn, task_id)
    dispatch = kb.dispatch_once(
        conn,
        max_spawn=1,
        max_in_progress=1,
        board=environment.board,
    )
    if not any(row[0] == task_id for row in dispatch.spawned):
        raise RuntimeError(f"dispatcher did not spawn {task_id}: {dispatch}")
    terminal = {"done", "blocked", "failed", "archived"}
    current = None
    while time.monotonic() - started < config.timeout_seconds:
        conn.close()
        time.sleep(1)
        conn = kb.connect(board=environment.board)
        current = kb.get_task(conn, task_id)
        if current is not None and current.status in terminal:
            break
    else:
        raise TimeoutError(f"consumer {task_id} did not finish")
    _wait_worker_exit(current)
    kb.reap_worker_zombies()
    runs = kb.list_runs(conn, task_id)
    run = runs[-1] if runs else None
    metadata = dict(run.metadata or {}) if run else {}
    session_id = str(metadata.get("worker_session_id") or "")
    session_id_source = "run_metadata"
    if not session_id:
        session_id = _single_consumer_session_id(environment)
        session_id_source = "sole_fresh_profile_session" if session_id else "missing"
    details = _session_details(environment.home, session_id)
    return (
        {
            "task_id": task_id,
            "status": current.status if current else "missing",
            "duration_seconds": round(time.monotonic() - started, 3),
            "summary": str(run.summary or "") if run else "",
            "metadata": metadata,
            "error": str(run.error or "") if run else "",
            "outcome": str(run.outcome or "") if run else "",
            "session_id": session_id,
            "session_id_source": session_id_source,
            "tool_trace": details["tools"],
            "tokens": details["tokens"],
            "session_found": details["session_found"],
            "log": _worker_log(environment.home, environment.board, task_id),
            "connection": conn,
        },
        preview,
    )


def _extract_handoff_block(text: str) -> str:
    start = text.find(HANDOFF_OPEN)
    end = text.find(HANDOFF_CLOSE, start + len(HANDOFF_OPEN))
    if start < 0 or end < 0:
        return ""
    return text[start : end + len(HANDOFF_CLOSE)]


def _scratchpad_projection(
    task: WorkflowTask,
) -> tuple[str, list[dict[str, Any]], bool]:
    store = WorkflowContextStore()
    workflow_id = f"{task.task_id}-v2"
    tx = store.begin(workflow_id, declared_writes=task.reads)
    if task.task_id == "multi_key_reconciliation":
        for key in task.reads:
            tx.stage(key, task.source[key])
    else:
        tx.stage("handoff", task.source)
    committed = tx.commit()
    view = store.view(workflow_id, declared_reads=task.reads)
    if task.task_id == "multi_key_reconciliation":
        readbacks = {key: view.read(key).payload for key in task.reads}
        text = "\n".join(
            f'<scratchpad key="{key}">'
            + readbacks[key].decode("utf-8")
            + "</scratchpad>"
            for key in task.reads
        )
        exact = all(
            readbacks[key] == canonical_bytes(task.source[key]) for key in task.reads
        )
        reconstructed = {
            key: json.loads(readbacks[key].decode("utf-8")) for key in task.reads
        }
        readback = canonical_bytes(reconstructed)
    else:
        readback = view.read("handoff").payload
        text = HANDOFF_OPEN + readback.decode("utf-8") + HANDOFF_CLOSE
        exact = text == _json_block(task.source)
    receipts = [
        {
            "hop": f"scratchpad:{value.key}",
            "byte_count": len(value.payload),
            "sha256": value.sha256,
        }
        for value in committed
    ]
    receipts.append({
        "hop": "scratchpad_readback",
        "byte_count": len(readback),
        "sha256": digest_bytes(readback),
    })
    return text, receipts, exact


def _file_identity(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": str(path.resolve()),
        "size": stat.st_size,
        "device": int(stat.st_dev),
        "inode": int(stat.st_ino),
        "mtime_ns": int(stat.st_mtime_ns),
        "sha256": digest_bytes(path.read_bytes()),
    }


def _path_within(candidate: Path, root: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def _resolve_trace_path(
    raw: str,
    environment: EvalEnvironment,
    config: RuntimeConfig,
    workspace: Path,
) -> Path:
    with _activate_environment(
        environment,
        config,
        profile="consumer",
        workspace=workspace,
        kanban_task="trace-resolution",
    ):
        from tools.file_tools import _resolve_path_for_task

        return Path(_resolve_path_for_task(raw, "trace-resolution")).resolve()


def _scope_trace(
    trace: list[dict[str, Any]],
    *,
    active_task_id: str,
    environment: EvalEnvironment,
    config: RuntimeConfig,
    shared_artifact: Path | None,
) -> dict[str, Any]:
    violations: list[dict[str, Any]] = []
    resolved_paths: list[dict[str, Any]] = []
    workspace = environment.consumer_workspace.resolve()
    shared = shared_artifact.resolve() if shared_artifact else None
    for call in trace:
        name = str(call.get("name") or "")
        arguments = call.get("arguments") or {}
        if name in FORBIDDEN_CONSUMER_TOOLS:
            violations.append({"tool": name, "reason": "forbidden_tool"})
            continue
        if name == "kanban_show":
            explicit = arguments.get("task_id") if isinstance(arguments, dict) else None
            if explicit and explicit != active_task_id:
                violations.append({"tool": name, "reason": "foreign_task_id"})
        if name.startswith("kanban_") and name not in ALLOWED_KANBAN_CALLS:
            violations.append({"tool": name, "reason": "forbidden_kanban_tool"})
        if name not in FILE_TOOLS:
            continue
        raw_paths: list[Any]
        if (
            name == "patch"
            and isinstance(arguments, dict)
            and arguments.get("mode") == "patch"
        ):
            content = arguments.get("patch")
            raw_paths = []
            if isinstance(content, str):
                raw_paths.extend(
                    match.group(2).strip()
                    for match in re.finditer(
                        r"^\*\*\*\s*(Update|Add|Delete)\s+File:\s*(.+)$",
                        content,
                        re.MULTILINE,
                    )
                )
                for match in re.finditer(
                    r"^\*\*\*\s*Move\s+File:\s*(.+?)\s*->\s*(.+)$",
                    content,
                    re.MULTILINE,
                ):
                    raw_paths.extend((match.group(1).strip(), match.group(2).strip()))
            if not raw_paths:
                violations.append({
                    "tool": name,
                    "reason": "unresolvable_patch_targets",
                })
                continue
        else:
            raw_paths = [
                arguments.get("path", ".") if isinstance(arguments, dict) else None
            ]
        for raw in raw_paths:
            if not isinstance(raw, str):
                violations.append({"tool": name, "reason": "unresolvable_path"})
                continue
            try:
                resolved = _resolve_trace_path(raw, environment, config, workspace)
            except Exception as exc:
                violations.append({
                    "tool": name,
                    "reason": "resolution_error",
                    "error": type(exc).__name__,
                })
                continue
            allowed = _path_within(resolved, workspace)
            if shared is not None and resolved == shared and name == "read_file":
                allowed = True
            resolved_paths.append({
                "tool": name,
                "raw": raw,
                "resolved": str(resolved),
                "allowed": allowed,
            })
            if not allowed:
                violations.append({"tool": name, "reason": "outside_allow_list"})
            if shared is not None and resolved == shared and name != "read_file":
                violations.append({
                    "tool": name,
                    "reason": "shared_artifact_mutation",
                })
    return {
        "ok": not violations,
        "violations": violations,
        "resolved_paths": resolved_paths,
    }


def _usage_total(card: dict[str, Any] | None) -> int | None:
    if not card or not card.get("session_found"):
        return None
    total = (card.get("tokens") or {}).get("total_tokens")
    if total is None or int(total) <= 0:
        return None
    return int(total)


def _relay_usage_total(relay: dict[str, Any]) -> int | None:
    total = (relay.get("tokens") or {}).get("total_tokens")
    if total is None or int(total) <= 0:
        return None
    return int(total)


def _cost_receipt_exact(record: dict[str, Any]) -> bool:
    segments = record.get("cost_segments") or {}
    duration_parts = (
        segments.get("common_producer_seconds"),
        segments.get("handoff_seconds"),
        segments.get("consumer_seconds"),
    )
    constructed = segments.get("constructed_total_seconds")
    if any(not isinstance(value, (int, float)) for value in duration_parts):
        return False
    if not isinstance(constructed, (int, float)):
        return False
    expected_duration = round(sum(float(value) for value in duration_parts), 6)
    if abs(float(constructed) - expected_duration) > 0.000002:
        return False
    duration = record.get("duration_seconds")
    if not isinstance(duration, (int, float)):
        return False
    if abs(float(duration) - expected_duration) > 0.000002:
        return False
    token_parts = (
        record.get("common_producer_tokens"),
        (record.get("consumer_tokens") or {}).get("total_tokens"),
        (record.get("parent_tokens") or {}).get("total_tokens"),
    )
    if any(not isinstance(value, int) for value in token_parts):
        return False
    return record.get("total_tokens") == sum(token_parts)


def _run_consumer(
    task: WorkflowTask,
    arm: str,
    *,
    config: RuntimeConfig,
    environment: EvalEnvironment,
    kb,
    producer: dict[str, Any] | None,
    producer_summary: str,
    producer_payload: bytes,
    shared_artifact: Path | None,
    common_tokens: int | None,
    common_duration: float,
) -> dict[str, Any]:
    handoff_started = time.monotonic()
    parent_tokens: dict[str, Any] = {"total_tokens": 0, "structural_zero": True}
    handoff_text: str | None = None
    handoff_receipts: list[dict[str, Any]] = []
    handoff_fidelity = True
    relay: dict[str, Any] | None = None
    if task.dependent and arm == "A":
        # Keep the parent model's session/config artifacts inside the disposable
        # A root without touching the consumer profile's empty session store.
        with _activate_environment(environment, config):
            relay = _parent_relay_v2(config, producer_summary)
        handoff_text = relay["text"]
        parent_tokens = dict(relay["tokens"])
        handoff_fidelity = handoff_text == _json_block(task.source)
        handoff_receipts.append({
            "hop": "parent_relay",
            "source_summary_sha256": digest_bytes(producer_summary.encode("utf-8")),
            "byte_count": len(handoff_text.encode("utf-8")),
            "sha256": digest_bytes(handoff_text.encode("utf-8")),
            "api_calls": relay["api_calls"],
        })
    elif task.dependent and arm == "C":
        handoff_text, handoff_receipts, handoff_fidelity = _scratchpad_projection(task)
    handoff_duration = round(time.monotonic() - handoff_started, 6)

    environment.consumer_workspace.mkdir(parents=True, exist_ok=True)
    write_json(
        environment.consumer_workspace / "consumer_input.json", task.consumer_local
    )
    parents = (
        (producer["task_id"],)
        if task.dependent and arm == "B" and task.topology == "detached_source"
        else ()
    )
    body = _consumer_body_v2(task, arm, handoff_text, shared_artifact)
    with _activate_environment(environment, config):
        conn = kb.connect(board=environment.board)
        consumer, preview = _run_card_with_preview(
            kb,
            conn,
            config=config,
            environment=environment,
            title=f"V2 consume {task.task_id}/{arm}",
            body=body,
            parents=parents,
        )
        conn = consumer.pop("connection")
        result_path = environment.consumer_workspace / "result.json"
        result_exact = result_path.is_file() and read_json(result_path) == task.expected
        result_digest = (
            digest_bytes(canonical_bytes(read_json(result_path)))
            if result_path.is_file()
            else ""
        )
        conn.close()

    context_manifest: dict[str, bool] = {}
    trace_scope = _scope_trace(
        consumer["tool_trace"],
        active_task_id=consumer["task_id"],
        environment=environment,
        config=config,
        shared_artifact=(
            shared_artifact
            if arm == "B" and task.topology == "shared_storage"
            else None
        ),
    )
    if task.dependent and arm == "B" and task.topology == "detached_source":
        projected = _extract_handoff_block(preview)
        handoff_fidelity = projected == _json_block(task.source)
        handoff_receipts.append({
            "hop": "kanban_projection",
            "source_summary_sha256": digest_bytes(producer_summary.encode("utf-8")),
            "byte_count": len(projected.encode("utf-8")),
            "sha256": digest_bytes(projected.encode("utf-8")),
        })
        context_manifest = {
            "parent_results": "## Parent task results" in preview,
            "no_prior_attempts": "## Prior attempts on this task" not in preview,
            "no_role_history": "## Recent work by @consumer" not in preview,
            "no_comments": "## Comment thread" not in preview,
        }
    elif task.dependent and arm == "B" and task.topology == "shared_storage":
        reads = [
            item
            for item in trace_scope["resolved_paths"]
            if item["tool"] == "read_file"
            and Path(item["resolved"]) == shared_artifact.resolve()
            and item["allowed"]
        ]
        handoff_fidelity = (
            bool(reads)
            and shared_artifact is not None
            and (shared_artifact.read_bytes() == producer_payload)
        )
        handoff_receipts.append({
            "hop": "shared_artifact_read",
            "read_calls": len(reads),
            "sha256": digest_bytes(shared_artifact.read_bytes())
            if shared_artifact and shared_artifact.is_file()
            else "",
        })

    files = _tree_files(environment.consumer_workspace)
    allowed_files = {"consumer_input.json", "result.json"}
    extra_files = sorted(set(files) - allowed_files)
    checks = {
        "status_done": consumer["status"] == "done",
        "show_first": bool(consumer["tool_trace"])
        and consumer["tool_trace"][0]["name"] == "kanban_show",
        "completed_via_tool": any(
            call["name"] == "kanban_complete" for call in consumer["tool_trace"]
        ),
        "result_exact": result_exact,
        "no_extra_files": not extra_files,
        "trace_scope": trace_scope["ok"],
        "clean_context": not context_manifest or all(context_manifest.values()),
    }
    ok = all(checks.values())
    false_success = not ok and (
        consumer["status"] == "done"
        or consumer["summary"].strip() == "consumer-complete"
    )
    consumer_total = _usage_total(consumer)
    relay_total = _relay_usage_total(relay) if relay else 0
    if common_tokens is None or consumer_total is None or relay_total is None:
        total_tokens = None
    else:
        total_tokens = common_tokens + consumer_total + relay_total
    constructed_duration = round(
        common_duration + handoff_duration + float(consumer["duration_seconds"]), 6
    )
    return {
        "task": task.task_id,
        "arm": arm,
        "topology": task.topology,
        "dependent": task.dependent,
        "ok": ok,
        "false_success": false_success,
        "scope_expansion": bool(extra_files) or not trace_scope["ok"],
        "handoff_fidelity": handoff_fidelity,
        "consumer": consumer,
        "consumer_checks": checks,
        "context_manifest": context_manifest,
        "context_receipts": handoff_receipts,
        "trace_scope": trace_scope,
        "parent_tokens": parent_tokens,
        "consumer_tokens": consumer.get("tokens") or {},
        "common_producer_tokens": common_tokens,
        "total_tokens": total_tokens,
        "cost_segments": {
            "common_producer_seconds": common_duration,
            "handoff_seconds": handoff_duration,
            "consumer_seconds": consumer["duration_seconds"],
            "constructed_total_seconds": constructed_duration,
        },
        "duration_seconds": constructed_duration,
        "consumer_files": files,
        "extra_files": extra_files,
        "expected_digest": digest_bytes(canonical_bytes(task.expected)),
        "result_digest": result_digest,
        "provider_failure": _provider_failure(
            consumer.get("error", ""), consumer.get("log", "")
        ),
    }


def run_fixture_v2(
    task: WorkflowTask,
    schedule_seed: int,
    config: RuntimeConfig,
    *,
    preflight: bool = False,
) -> dict[str, Any]:
    fixture_root = Path(tempfile.mkdtemp(prefix=f"shared-context-v2-{task.task_id}-"))
    environments: dict[str, EvalEnvironment] = {}
    conn = None
    try:
        for arm in "ABC":
            environments[arm] = _make_environment(
                fixture_root,
                arm,
                config,
                include_producer=arm == "B" and task.dependent,
            )
        kb = _load_target(config)
        schemas = {
            arm: _schema_receipt(environment, config)
            for arm, environment in environments.items()
        }
        schema_hashes = {receipt["schema_sha256"] for receipt in schemas.values()}
        config_hashes = {receipt["config_sha256"] for receipt in schemas.values()}
        schemas_equal = len(schema_hashes) == len(config_hashes) == 1
        schemas_safe = schemas_equal and all(
            receipt["forbidden_absent"]
            and receipt["required_present"]
            and receipt["surface_bounded"]
            for receipt in schemas.values()
        )

        producer: dict[str, Any] | None = None
        producer_payload = b""
        producer_summary = ""
        producer_workspace: Path | None = None
        shared_artifact: Path | None = None
        producer_file_identity: dict[str, Any] | None = None
        common_tokens: int | None = 0
        common_duration = 0.0
        producer_checks: dict[str, bool] = {}
        if task.dependent:
            b_environment = environments["B"]
            producer_workspace = b_environment.root / (
                "shared-artifact"
                if task.topology == "shared_storage"
                else "producer-workspace"
            )
            producer_workspace.mkdir(parents=True)
            write_json(producer_workspace / "source.json", task.source)
            with _activate_environment(b_environment, config):
                conn = kb.connect(board=b_environment.board)
                producer = _run_card(
                    kb,
                    conn,
                    config=config,
                    home=b_environment.home,
                    board=b_environment.board,
                    title=f"V2 produce {task.task_id}",
                    body=_producer_body_v2(task),
                    assignee="producer",
                    workspace=producer_workspace,
                )
                conn = producer.pop("connection")
                conn.close()
                conn = None
            handoff_path = producer_workspace / "handoff.json"
            producer_payload = (
                handoff_path.read_bytes() if handoff_path.is_file() else b""
            )
            producer_summary = producer["summary"]
            expected_payload = canonical_bytes(task.source)
            producer_checks = {
                "status_done": producer["status"] == "done",
                "show_first": bool(producer["tool_trace"])
                and producer["tool_trace"][0]["name"] == "kanban_show",
                "completed_via_tool": any(
                    call["name"] == "kanban_complete" for call in producer["tool_trace"]
                ),
                "handoff_parses_exact": handoff_path.is_file()
                and read_json(handoff_path) == task.source,
                "digest_exact": digest_bytes(producer_payload)
                == digest_bytes(expected_payload),
                "only_declared_files": set(_tree_files(producer_workspace))
                <= {"source.json", "handoff.json"},
            }
            producer["checks"] = producer_checks
            producer["summary_sha256"] = digest_bytes(producer_summary.encode("utf-8"))
            producer["artifact_sha256"] = digest_bytes(producer_payload)
            producer["summary_exact"] = producer_summary == _json_block(task.source)
            common_tokens = _usage_total(producer)
            common_duration = float(producer["duration_seconds"])
            if (producer_workspace / "source.json").exists():
                (producer_workspace / "source.json").unlink()
            if task.topology == "detached_source":
                _remove_tree(producer_workspace)
            else:
                shared_artifact = handoff_path
                producer_file_identity = _file_identity(shared_artifact)

        admitted = not task.dependent or all(producer_checks.values())
        provider_failure = _provider_failure(
            producer.get("error", "") if producer else "",
            producer.get("log", "") if producer else "",
        )
        if not admitted or provider_failure:
            return {
                "task": task.task_id,
                "schedule_seed": schedule_seed,
                "topology": task.topology,
                "dependent": task.dependent,
                "preflight": preflight,
                "order": list(arm_order(task.task_id, schedule_seed)),
                "producer": producer,
                "producer_admitted": admitted,
                "producer_checks": producer_checks,
                "schemas": schemas,
                "schemas_safe_equal": schemas_safe,
                "provider_failure": provider_failure,
                "arms": {},
                "integrity": {"producer_admitted": admitted},
            }

        pre_counts = {
            arm: {
                "consumer_sessions": _profile_session_count(environment),
                "tasks": _task_count(kb, environment, config),
            }
            for arm, environment in environments.items()
        }
        sentinel: dict[str, Any] = {}
        if task.dependent and producer:
            sentinel = {
                arm: _show_probe(environment, config, producer["task_id"])
                for arm, environment in environments.items()
            }

        arms: dict[str, dict[str, Any]] = {}
        for arm in arm_order(task.task_id, schedule_seed):
            arms[arm] = _run_consumer(
                task,
                arm,
                config=config,
                environment=environments[arm],
                kb=kb,
                producer=producer,
                producer_summary=producer_summary,
                producer_payload=producer_payload,
                shared_artifact=shared_artifact,
                common_tokens=common_tokens,
                common_duration=common_duration,
            )
            arms[arm]["schedule_position"] = len(arms)
            arms[arm]["profile_receipt"] = schemas[arm]
            arms[arm]["pre_run_counts"] = pre_counts[arm]

        shared_identity_after = (
            _file_identity(shared_artifact)
            if shared_artifact is not None and shared_artifact.is_file()
            else None
        )
        common_costs_equal = (
            len({
                (
                    record["common_producer_tokens"],
                    record["cost_segments"]["common_producer_seconds"],
                )
                for record in arms.values()
            })
            == 1
        )
        homes_distinct = (
            len({str(value.home.resolve()) for value in environments.values()}) == 3
        )
        dbs_distinct = (
            len({str(value.database.resolve()) for value in environments.values()}) == 3
        )
        workspaces_distinct = (
            len({
                str(value.consumer_workspace.resolve())
                for value in environments.values()
            })
            == 3
        )
        sentinel_ok = True
        if task.dependent:
            sentinel_ok = (
                sentinel["A"]["not_found"]
                and sentinel["C"]["not_found"]
                and sentinel["B"]["found"]
            )
        shared_identity_ok = True
        if task.dependent and task.topology == "shared_storage":
            shared_identity_ok = (
                producer_file_identity is not None
                and shared_identity_after is not None
                and producer_file_identity == shared_identity_after
                and arms["B"]["handoff_fidelity"]
            )
        summary_reference_ok = True
        if task.dependent and task.topology == "detached_source":
            expected_summary = producer["summary_sha256"] if producer else ""
            summary_reference_ok = all(
                any(
                    receipt.get("source_summary_sha256") == expected_summary
                    for receipt in arms[arm]["context_receipts"]
                )
                for arm in ("A", "B")
            )
        scratchpad_digest_ok = True
        if task.dependent:
            expected_artifact = producer["artifact_sha256"] if producer else ""
            scratchpad_digest_ok = any(
                receipt.get("hop") == "scratchpad_readback"
                and receipt.get("sha256") == expected_artifact
                for receipt in arms["C"]["context_receipts"]
            )
        cost_segments_exact = all(
            _cost_receipt_exact(record) for record in arms.values()
        )
        detached_removed = not (
            task.dependent
            and task.topology == "detached_source"
            and producer_workspace is not None
            and producer_workspace.exists()
        )
        integrity = {
            "producer_admitted": admitted,
            "exactly_one_producer": not task.dependent
            or (producer is not None and int(pre_counts["B"]["tasks"]) == 1),
            "schemas_safe_equal": schemas_safe,
            "overrides_equal": len({
                (
                    receipt["provider_override"],
                    receipt["model_override"],
                    receipt["max_iterations"],
                    receipt["profile"],
                )
                for receipt in schemas.values()
            })
            == 1,
            "homes_distinct": homes_distinct,
            "dbs_distinct": dbs_distinct,
            "workspaces_distinct": workspaces_distinct,
            "empty_consumer_sessions": all(
                counts["consumer_sessions"] == 0 for counts in pre_counts.values()
            ),
            "expected_pre_run_task_counts": (
                (
                    pre_counts["A"]["tasks"],
                    pre_counts["B"]["tasks"],
                    pre_counts["C"]["tasks"],
                )
                == ((0, 1, 0) if task.dependent else (0, 0, 0))
            ),
            "sentinel": sentinel_ok,
            "common_costs_equal": common_costs_equal,
            "order_exact": tuple(arms) == arm_order(task.task_id, schedule_seed),
            "all_trace_scopes": all(
                record["trace_scope"]["ok"] for record in arms.values()
            ),
            "shared_identity": shared_identity_ok,
            "same_summary_reference": summary_reference_ok,
            "scratchpad_digest_exact": scratchpad_digest_ok,
            "cost_segments_exact": cost_segments_exact,
            "detached_source_removed": detached_removed,
            "controls_have_no_handoff": task.dependent
            or all(not record["context_receipts"] for record in arms.values()),
        }
        return {
            "task": task.task_id,
            "schedule_seed": schedule_seed,
            "topology": task.topology,
            "dependent": task.dependent,
            "preflight": preflight,
            "order": list(arm_order(task.task_id, schedule_seed)),
            "producer": producer,
            "producer_admitted": admitted,
            "producer_checks": producer_checks,
            "producer_file_identity": producer_file_identity,
            "shared_file_identity_after": shared_identity_after,
            "schemas": schemas,
            "schemas_safe_equal": schemas_safe,
            "pre_run_counts": pre_counts,
            "sentinel": sentinel,
            "common_producer_tokens": common_tokens,
            "common_producer_duration_seconds": common_duration,
            "arms": arms,
            "integrity": integrity,
            "provider_failure": next(
                (
                    record["provider_failure"]
                    for record in arms.values()
                    if record.get("provider_failure")
                ),
                None,
            ),
        }
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
        shutil.rmtree(fixture_root, ignore_errors=True)
