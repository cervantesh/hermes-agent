"""Real-path Kanban runtime for the sealed A/B/C experiment."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import time
from typing import Any, Iterator

from .shared_context import WorkflowContextStore, canonical_bytes, digest_bytes
from .tasks import WorkflowTask, consumer_operation, read_json, write_json


PROTOCOL_TARGET = "180291162ff4df0d42b5dc4fecd08005cf7cebf9"
HANDOFF_OPEN = "<handoff-json>"
HANDOFF_CLOSE = "</handoff-json>"
PROVIDER_FAILURE_MARKERS = (
    "authentication failed",
    "connection error",
    "rate limit",
    "quota exceeded",
    "resource_exhausted",
    "api call failed after",
)


@dataclass(frozen=True)
class RuntimeConfig:
    repo_root: Path
    python_executable: Path
    model: str = "claude-haiku-4-5"
    provider: str = "claude-code"
    max_iterations: int = 30
    timeout_seconds: int = 600


def _provider_override(provider: str) -> str:
    return "anthropic" if provider == "claude-code" else provider


def _json_block(value: Any) -> str:
    return HANDOFF_OPEN + canonical_bytes(value).decode("utf-8") + HANDOFF_CLOSE


def _tree_files(root: Path) -> list[str]:
    if not root.exists():
        return []
    return sorted(
        str(path.relative_to(root)).replace("\\", "/")
        for path in root.rglob("*")
        if path.is_file()
    )


@contextmanager
def _experiment_environment(
    root: Path, config: RuntimeConfig
) -> Iterator[dict[str, Path]]:
    home = root / "home"
    board_workspaces = root / "board-workspaces"
    home.mkdir(parents=True)
    board_workspaces.mkdir(parents=True)
    profile_config = f"agent:\n  max_turns: {config.max_iterations}\n"
    for profile in ("producer", "consumer"):
        profile_root = home / "profiles" / profile
        profile_root.mkdir(parents=True)
        (profile_root / "config.yaml").write_text(profile_config, encoding="utf-8")
    (home / "config.yaml").write_text(profile_config, encoding="utf-8")
    board = "shared-context-eval"
    updates = {
        "HERMES_HOME": str(home),
        "HERMES_KANBAN_DB": str(root / "kanban.db"),
        "HERMES_KANBAN_WORKSPACES_ROOT": str(board_workspaces),
        "HERMES_KANBAN_BOARD": board,
        "HERMES_MAX_ITERATIONS": str(config.max_iterations),
        "PYTHONPATH": str(config.repo_root),
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    scripts = str(config.python_executable.parent)
    updates["PATH"] = scripts + os.pathsep + os.environ.get("PATH", "")
    old = dict(os.environ)
    os.environ.update(updates)
    try:
        yield {"home": home, "board_workspaces": board_workspaces, "board": Path(board)}
    finally:
        os.environ.clear()
        os.environ.update(old)


def _load_target(config: RuntimeConfig):
    repo = str(config.repo_root)
    if repo not in sys.path:
        sys.path.insert(0, repo)
    from hermes_cli import kanban_db as kb

    return kb


def _session_details(home: Path, session_id: str) -> dict[str, Any]:
    candidates = [home / "state.db"] + sorted((home / "profiles").glob("*/state.db"))
    db_path = next((path for path in candidates if path.is_file()), None)
    if db_path is None or not session_id:
        return {"tools": [], "tokens": {}, "session_found": False}
    for candidate in candidates:
        if not candidate.is_file():
            continue
        conn = sqlite3.connect(candidate)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT 1 FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if row:
            db_path = candidate
            conn.close()
            break
        conn.close()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT role, tool_name, tool_calls, finish_reason FROM messages "
            "WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
        trace: list[dict[str, Any]] = []
        for row in rows:
            raw_calls = row["tool_calls"]
            if raw_calls:
                try:
                    calls = json.loads(raw_calls)
                except (TypeError, ValueError):
                    calls = []
                for call in calls:
                    function = call.get("function") or {}
                    raw_args = function.get("arguments") or call.get("arguments")
                    try:
                        arguments = (
                            json.loads(raw_args)
                            if isinstance(raw_args, str)
                            else raw_args
                        )
                    except (TypeError, ValueError):
                        arguments = {"_unparsed": True}
                    trace.append({
                        "name": function.get("name") or call.get("name") or "unknown",
                        "arguments": arguments,
                    })
        usage = conn.execute(
            "SELECT api_call_count, input_tokens, output_tokens, cache_read_tokens, "
            "cache_write_tokens, reasoning_tokens, estimated_cost_usd "
            "FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        tokens = dict(usage) if usage else {}
        if tokens:
            numeric = (
                "input_tokens",
                "output_tokens",
                "cache_read_tokens",
                "cache_write_tokens",
                "reasoning_tokens",
            )
            tokens["total_tokens"] = sum(int(tokens.get(key) or 0) for key in numeric)
        return {"tools": trace, "tokens": tokens, "session_found": bool(usage)}
    finally:
        conn.close()


def _worker_log(home: Path, board: str, task_id: str) -> str:
    path = home / "kanban" / "boards" / board / "logs" / f"{task_id}.log"
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _wait_worker_exit(task, timeout: float = 30.0) -> None:
    pid = int(getattr(task, "worker_pid", 0) or 0)
    if not pid:
        return
    import psutil

    try:
        psutil.Process(pid).wait(timeout=timeout)
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return
    except psutil.TimeoutExpired as exc:
        raise TimeoutError(
            f"worker process {pid} remained alive after completion"
        ) from exc


def _remove_tree(path: Path, timeout: float = 15.0) -> None:
    deadline = time.monotonic() + timeout
    while True:
        try:
            shutil.rmtree(path)
            return
        except FileNotFoundError:
            return
        except PermissionError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.25)


def _run_card(
    kb,
    conn,
    *,
    config: RuntimeConfig,
    home: Path,
    board: str,
    title: str,
    body: str,
    assignee: str,
    workspace: Path,
    parents: tuple[str, ...] = (),
) -> dict[str, Any]:
    workspace.mkdir(parents=True, exist_ok=True)
    task_id = kb.create_task(
        conn,
        title=title,
        body=body,
        assignee=assignee,
        created_by="shared-context-research",
        workspace_kind="dir",
        workspace_path=str(workspace),
        parents=parents,
        max_runtime_seconds=config.timeout_seconds,
        model_override=config.model,
        provider_override=_provider_override(config.provider),
        board=board,
    )
    started = time.monotonic()
    dispatch = kb.dispatch_once(
        conn,
        max_spawn=1,
        max_in_progress=1,
        board=board,
    )
    if not any(row[0] == task_id for row in dispatch.spawned):
        raise RuntimeError(f"dispatcher did not spawn {task_id}: {dispatch}")
    terminal = {"done", "blocked", "failed", "archived"}
    while time.monotonic() - started < config.timeout_seconds:
        conn.close()
        time.sleep(1)
        conn = kb.connect(board=board)
        task = kb.get_task(conn, task_id)
        if task is not None and task.status in terminal:
            break
    else:
        raise TimeoutError(f"worker did not finish within {config.timeout_seconds}s")
    _wait_worker_exit(task)
    kb.reap_worker_zombies()
    runs = kb.list_runs(conn, task_id)
    run = runs[-1] if runs else None
    metadata = dict(run.metadata or {}) if run else {}
    session_id = str(metadata.get("worker_session_id") or "")
    session = _session_details(home, session_id)
    log = _worker_log(home, board, task_id)
    return {
        "task_id": task_id,
        "status": task.status if task else "missing",
        "duration_seconds": round(time.monotonic() - started, 3),
        "summary": str(run.summary or "") if run else "",
        "metadata": metadata,
        "error": str(run.error or "") if run else "",
        "outcome": str(run.outcome or "") if run else "",
        "session_id": session_id,
        "tool_trace": session["tools"],
        "tokens": session["tokens"],
        "session_found": session["session_found"],
        "log": log,
        "connection": conn,
    }


def _producer_body(task: WorkflowTask) -> str:
    payload = canonical_bytes(task.source)
    block = _json_block(task.source)
    digest = digest_bytes(payload)
    return (
        "Call kanban_show() first. Read source.json and create handoff.json with "
        "exactly the same canonical JSON value. Do not add or remove fields. "
        "Then call kanban_complete. Its summary must be exactly the delimited "
        f"block below, with no surrounding prose:\n{block}\n"
        "Its metadata must contain exactly these research fields (the tool may "
        "add its own lifecycle fields): "
        f'{{"byte_count":{len(payload)},"sha256":"{digest}"}}. '
        "Do not pass an artifacts list and do not create any other workspace file."
    )


def _consumer_body(task: WorkflowTask, arm: str, handoff_text: str | None) -> str:
    if not task.dependent:
        source = "There is no upstream dependency. Do not look for handoff state."
    elif arm == "B" and task.topology == "shared_storage":
        source = "Use handoff.json in the assigned workspace as the upstream value."
    elif arm == "B":
        source = (
            "Use the canonical handoff block under `## Parent task results` in "
            "the output of kanban_show()."
        )
    else:
        source = (
            "Use only the following treatment handoff; do not read handoff.json "
            f"from the workspace:\n{handoff_text or ''}"
        )
    return (
        "Call kanban_show() first. "
        + source
        + " Read consumer_input.json. "
        + consumer_operation(task)
        + " Write result.json as canonical or pretty JSON containing exactly the "
        "requested keys and values. Then call kanban_complete with summary "
        "exactly consumer-complete and metadata containing exactly the fields "
        + f'{{"arm":"{arm}","task":"{task.task_id}"}}. '
        "Do not pass an artifacts list and do not create any other workspace file."
    )


def _parent_relay(config: RuntimeConfig, block: str) -> dict[str, Any]:
    from run_agent import AIAgent

    kwargs: dict[str, Any]
    if config.provider == "claude-code":
        kwargs = {
            "provider": "anthropic",
            "model": config.model,
            "api_key": None,
            "api_mode": "anthropic_messages",
        }
    else:
        key = os.environ.get(f"{config.provider.upper()}_API_KEY")
        kwargs = {"provider": config.provider, "model": config.model, "api_key": key}
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
    raw_tokens = result.get("tokens") or result.get("token_usage") or {}
    tokens = {
        str(key): value for key, value in raw_tokens.items() if isinstance(value, int)
    }
    if tokens and "total_tokens" not in tokens:
        tokens["total_tokens"] = sum(tokens.values())
    return {
        "text": str(result.get("final_response") or ""),
        "tokens": tokens,
        "api_calls": int(result.get("api_calls") or 0),
    }


def _provider_failure(*materials: str) -> str | None:
    text = "\n".join(materials).lower()
    return next((marker for marker in PROVIDER_FAILURE_MARKERS if marker in text), None)


def _forbidden_artifact_read(trace: list[dict[str, Any]], workspace: Path) -> bool:
    target = str((workspace / "handoff.json").resolve()).lower()
    for call in trace:
        if call.get("name") not in {"read_file", "terminal"}:
            continue
        material = json.dumps(call.get("arguments"), ensure_ascii=False).lower()
        if "handoff.json" in material or target in material:
            return True
    return False


def run_observation(
    task: WorkflowTask, arm: str, config: RuntimeConfig
) -> dict[str, Any]:
    if arm not in {"A", "B", "C"}:
        raise ValueError(f"unknown arm: {arm}")
    root = Path(tempfile.mkdtemp(prefix=f"shared-context-{task.task_id}-{arm}-"))
    started = time.monotonic()
    conn = None
    try:
        with _experiment_environment(root, config) as paths:
            kb = _load_target(config)
            board = paths["board"].name
            conn = kb.connect(board=board)
            producer: dict[str, Any] | None = None
            parent_tokens: dict[str, Any] = {}
            relay_text: str | None = None
            context_receipts: list[dict[str, Any]] = []
            handoff_fidelity = True
            producer_workspace = root / "producer-workspace"
            consumer_workspace = (
                producer_workspace
                if task.topology == "shared_storage" and task.dependent
                else root / "consumer-workspace"
            )

            if task.dependent:
                producer_workspace.mkdir(parents=True)
                write_json(producer_workspace / "source.json", task.source)
                producer = _run_card(
                    kb,
                    conn,
                    config=config,
                    home=paths["home"],
                    board=board,
                    title=f"Produce handoff for {task.task_id}",
                    body=_producer_body(task),
                    assignee="producer",
                    workspace=producer_workspace,
                )
                conn = producer.pop("connection")
                handoff_path = producer_workspace / "handoff.json"
                handoff_exact = (
                    handoff_path.is_file() and read_json(handoff_path) == task.source
                )
                payload = handoff_path.read_bytes() if handoff_path.is_file() else b""
                expected_block = _json_block(task.source)
                summary_exact = producer["summary"] == expected_block
                producer["checks"] = {
                    "status_done": producer["status"] == "done",
                    "show_first": bool(producer["tool_trace"])
                    and producer["tool_trace"][0]["name"] == "kanban_show",
                    "completed_via_tool": any(
                        call["name"] == "kanban_complete"
                        for call in producer["tool_trace"]
                    ),
                    "handoff_exact": handoff_exact,
                    "summary_exact": summary_exact,
                    "digest_exact": digest_bytes(payload)
                    == digest_bytes(canonical_bytes(task.source)),
                }
                context_receipts.append({
                    "hop": "producer_artifact",
                    "byte_count": len(payload),
                    "sha256": digest_bytes(payload),
                })
                if arm == "A":
                    relay = _parent_relay(config, producer["summary"])
                    relay_text = relay["text"]
                    parent_tokens = relay["tokens"]
                    context_receipts.append({
                        "hop": "parent_relay",
                        "byte_count": len(relay_text.encode("utf-8")),
                        "sha256": digest_bytes(relay_text.encode("utf-8")),
                        "api_calls": relay["api_calls"],
                    })
                    handoff_fidelity = relay_text == expected_block
                elif arm == "C":
                    store = WorkflowContextStore()
                    workflow_id = f"{task.task_id}-workflow"
                    tx = store.begin(workflow_id, declared_writes=task.reads)
                    if task.task_id == "multi_key_reconciliation":
                        for key in task.reads:
                            tx.stage(key, task.source[key])
                    else:
                        tx.stage("handoff", task.source)
                    committed = tx.commit()
                    view = store.view(workflow_id, declared_reads=task.reads)
                    if task.task_id == "multi_key_reconciliation":
                        relay_text = "\n".join(
                            f'<scratchpad key="{key}">'
                            + view.read(key).payload.decode("utf-8")
                            + "</scratchpad>"
                            for key in task.reads
                        )
                    else:
                        relay_text = (
                            HANDOFF_OPEN
                            + view.read("handoff").payload.decode("utf-8")
                            + HANDOFF_CLOSE
                        )
                    context_receipts.extend(
                        {
                            "hop": f"scratchpad:{value.key}",
                            "byte_count": len(value.payload),
                            "sha256": value.sha256,
                        }
                        for value in committed
                    )
                    if task.task_id == "multi_key_reconciliation":
                        handoff_fidelity = all(
                            view.read(key).payload == canonical_bytes(task.source[key])
                            for key in task.reads
                        )
                    else:
                        handoff_fidelity = relay_text == expected_block

                if arm == "B" and task.topology == "shared_storage":
                    handoff_fidelity = handoff_exact
                    context_receipts.append({
                        "hop": "shared_artifact",
                        "byte_count": len(payload),
                        "sha256": digest_bytes(payload),
                    })

                if (producer_workspace / "source.json").exists():
                    (producer_workspace / "source.json").unlink()
                if task.topology == "detached_source":
                    _remove_tree(producer_workspace)

            consumer_workspace.mkdir(parents=True, exist_ok=True)
            write_json(consumer_workspace / "consumer_input.json", task.consumer_local)
            parents: tuple[str, ...] = ()
            context_manifest: dict[str, bool] = {}
            if task.dependent and arm == "B" and task.topology == "detached_source":
                parents = (producer["task_id"],) if producer else ()
                preview_id = kb.create_task(
                    conn,
                    title=f"Consume handoff for {task.task_id}",
                    body=_consumer_body(task, arm, relay_text),
                    assignee="consumer",
                    created_by="shared-context-research",
                    workspace_kind="dir",
                    workspace_path=str(consumer_workspace),
                    parents=parents,
                    max_runtime_seconds=config.timeout_seconds,
                    model_override=config.model,
                    provider_override=_provider_override(config.provider),
                    board=board,
                )
                preview = kb.build_worker_context(conn, preview_id)
                start = preview.find(HANDOFF_OPEN)
                end = preview.find(HANDOFF_CLOSE, start + len(HANDOFF_OPEN))
                projected = (
                    preview[start : end + len(HANDOFF_CLOSE)]
                    if start >= 0 and end >= 0
                    else ""
                )
                handoff_fidelity = projected == _json_block(task.source)
                context_receipts.append({
                    "hop": "kanban_projection",
                    "byte_count": len(projected.encode("utf-8")),
                    "sha256": digest_bytes(projected.encode("utf-8")),
                })
                context_manifest = {
                    "parent_results": "## Parent task results" in preview,
                    "no_prior_attempts": "## Prior attempts on this task"
                    not in preview,
                    "no_role_history": "## Recent work by @consumer" not in preview,
                    "no_comments": "## Comment thread" not in preview,
                }
                # Dispatch the already-created card rather than creating it twice.
                consumer_started = time.monotonic()
                dispatch = kb.dispatch_once(
                    conn, max_spawn=1, max_in_progress=1, board=board
                )
                if not any(row[0] == preview_id for row in dispatch.spawned):
                    raise RuntimeError(f"dispatcher did not spawn {preview_id}")
                terminal = {"done", "blocked", "failed", "archived"}
                while time.monotonic() - consumer_started < config.timeout_seconds:
                    conn.close()
                    time.sleep(1)
                    conn = kb.connect(board=board)
                    current = kb.get_task(conn, preview_id)
                    if current is not None and current.status in terminal:
                        break
                else:
                    raise TimeoutError(f"consumer {preview_id} did not finish")
                _wait_worker_exit(current)
                kb.reap_worker_zombies()
                runs = kb.list_runs(conn, preview_id)
                run = runs[-1] if runs else None
                metadata = dict(run.metadata or {}) if run else {}
                sid = str(metadata.get("worker_session_id") or "")
                details = _session_details(paths["home"], sid)
                consumer = {
                    "task_id": preview_id,
                    "status": current.status if current else "missing",
                    "duration_seconds": round(time.monotonic() - consumer_started, 3),
                    "summary": str(run.summary or "") if run else "",
                    "metadata": metadata,
                    "error": str(run.error or "") if run else "",
                    "outcome": str(run.outcome or "") if run else "",
                    "session_id": sid,
                    "tool_trace": details["tools"],
                    "tokens": details["tokens"],
                    "session_found": details["session_found"],
                    "log": _worker_log(paths["home"], board, preview_id),
                }
            else:
                consumer = _run_card(
                    kb,
                    conn,
                    config=config,
                    home=paths["home"],
                    board=board,
                    title=f"Consume handoff for {task.task_id}",
                    body=_consumer_body(task, arm, relay_text),
                    assignee="consumer",
                    workspace=consumer_workspace,
                )
                conn = consumer.pop("connection")

            result_path = consumer_workspace / "result.json"
            result_exact = (
                result_path.is_file() and read_json(result_path) == task.expected
            )
            consumer_files = _tree_files(consumer_workspace)
            allowed = {"consumer_input.json", "result.json"}
            if task.dependent and task.topology == "shared_storage":
                allowed.add("handoff.json")
            scope_expansion = bool(set(consumer_files) - allowed)
            forbidden_read = bool(
                task.dependent
                and task.topology == "shared_storage"
                and arm in {"A", "C"}
                and _forbidden_artifact_read(consumer["tool_trace"], consumer_workspace)
            )
            consumer_checks = {
                "status_done": consumer["status"] == "done",
                "show_first": bool(consumer["tool_trace"])
                and consumer["tool_trace"][0]["name"] == "kanban_show",
                "completed_via_tool": any(
                    call["name"] == "kanban_complete" for call in consumer["tool_trace"]
                ),
                "result_exact": result_exact,
                "no_scope_expansion": not scope_expansion,
                "no_forbidden_artifact_read": not forbidden_read,
            }
            if context_manifest:
                consumer_checks["clean_context_manifest"] = all(
                    context_manifest.values()
                )
            consumer["checks"] = consumer_checks
            producer_valid = producer is None or all(producer["checks"].values())
            ok = producer_valid and all(consumer_checks.values())
            false_success = not ok and (
                consumer["status"] == "done"
                or consumer["summary"].strip() == "consumer-complete"
            )
            failure = _provider_failure(
                producer["error"] if producer else "",
                producer["log"] if producer else "",
                consumer["error"],
                consumer["log"],
            )
            total_tokens = sum(
                int((part or {}).get("total_tokens") or 0)
                for part in (
                    producer.get("tokens") if producer else {},
                    consumer.get("tokens"),
                    parent_tokens,
                )
            )
            return {
                "task": task.task_id,
                "arm": arm,
                "topology": task.topology,
                "dependent": task.dependent,
                "ok": ok,
                "false_success": false_success,
                "scope_expansion": scope_expansion or forbidden_read,
                "handoff_fidelity": handoff_fidelity,
                "provider_failure": failure,
                "producer": producer,
                "consumer": consumer,
                "context_manifest": context_manifest,
                "context_receipts": context_receipts,
                "parent_tokens": parent_tokens,
                "total_tokens": total_tokens,
                "duration_seconds": round(time.monotonic() - started, 3),
                "consumer_files": consumer_files,
                "expected_digest": digest_bytes(canonical_bytes(task.expected)),
                "result_digest": digest_bytes(canonical_bytes(read_json(result_path)))
                if result_path.is_file()
                else "",
            }
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
        shutil.rmtree(root, ignore_errors=True)
