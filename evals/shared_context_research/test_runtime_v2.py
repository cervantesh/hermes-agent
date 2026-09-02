from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sqlite3

from . import runtime_v2
from .runtime import RuntimeConfig
from .runtime_v2 import (
    _cleanup_timed_out_consumer,
    _make_environment,
    _profile_session_count,
    _scope_trace,
    _scratchpad_projection,
    _show_response_state,
    _single_consumer_session_id,
)
from .shared_context import WorkflowContextStore, digest_bytes
from .tasks import TASKS_BY_ID


TARGET = Path(r"C:\dev\hermes-shared-context-main")
WORKER_PYTHON = Path(r"C:\dev\hermes\.venv\Scripts\python.exe")


def _config() -> RuntimeConfig:
    return RuntimeConfig(repo_root=TARGET, python_executable=WORKER_PYTHON)


class _TimeoutCleanupKB:
    def __init__(self, *, enforced: list[str], reclaimed: bool = True) -> None:
        self.enforced = enforced
        self.reclaimed = reclaimed
        self.reclaim_calls: list[tuple[str, str]] = []
        self.reap_calls = 0

    def enforce_max_runtime(self, _conn) -> list[str]:
        return self.enforced

    def reclaim_task(self, _conn, task_id: str, *, reason: str) -> bool:
        self.reclaim_calls.append((task_id, reason))
        return self.reclaimed

    def reap_worker_zombies(self) -> None:
        self.reap_calls += 1


def test_fixture_deadline_uses_kanban_timeout_cleanup() -> None:
    kb = _TimeoutCleanupKB(enforced=["consumer-task"])

    _cleanup_timed_out_consumer(kb, object(), "consumer-task")

    assert kb.reclaim_calls == []
    assert kb.reap_calls == 1


def test_fixture_deadline_reclaims_when_runtime_clock_has_not_elapsed() -> None:
    kb = _TimeoutCleanupKB(enforced=[])

    _cleanup_timed_out_consumer(kb, object(), "consumer-task")

    assert kb.reclaim_calls == [
        ("consumer-task", "shared-context research fixture deadline exceeded")
    ]
    assert kb.reap_calls == 1


def test_fixture_deadline_refuses_to_hide_failed_cleanup() -> None:
    kb = _TimeoutCleanupKB(enforced=[], reclaimed=False)

    try:
        _cleanup_timed_out_consumer(kb, object(), "consumer-task")
    except RuntimeError as exc:
        assert "could not be reclaimed" in str(exc)
    else:
        raise AssertionError("failed timeout cleanup must be visible")
    assert kb.reap_calls == 0


def test_uninitialized_profile_database_has_zero_sessions(tmp_path: Path) -> None:
    config = _config()
    environment = _make_environment(tmp_path, "A", config)
    state = environment.home / "profiles" / "consumer" / "state.db"
    state.touch()
    assert _profile_session_count(environment) == 0


def test_session_fallback_requires_exactly_one_fresh_profile_session(
    tmp_path: Path,
) -> None:
    config = _config()
    environment = _make_environment(tmp_path, "A", config)
    state = environment.home / "profiles" / "consumer" / "state.db"
    conn = sqlite3.connect(state)
    conn.execute("CREATE TABLE sessions (id TEXT PRIMARY KEY)")
    conn.commit()
    assert _single_consumer_session_id(environment) == ""
    conn.execute("INSERT INTO sessions (id) VALUES ('only-session')")
    conn.commit()
    assert _single_consumer_session_id(environment) == "only-session"
    conn.execute("INSERT INTO sessions (id) VALUES ('second-session')")
    conn.commit()
    conn.close()
    assert _single_consumer_session_id(environment) == ""


def test_cross_database_sentinel_parses_id_qualified_not_found() -> None:
    found, not_found = _show_response_state('{"error":"task producer-uuid not found"}')
    assert found is False
    assert not_found is True


def test_resolved_path_gate_rejects_traversal_and_forbidden_tools(
    tmp_path: Path,
) -> None:
    config = _config()
    environment = _make_environment(tmp_path, "A", config)
    environment.consumer_workspace.mkdir(parents=True)
    trace = [
        {"name": "read_file", "arguments": {"path": "consumer_input.json"}},
        {"name": "read_file", "arguments": {"path": "../outside.json"}},
        {"name": "terminal", "arguments": {"command": "dir .."}},
    ]
    receipt = _scope_trace(
        trace,
        active_task_id="consumer-task",
        environment=environment,
        config=config,
        shared_artifact=None,
    )
    assert receipt["ok"] is False
    reasons = {row["reason"] for row in receipt["violations"]}
    assert reasons == {"outside_allow_list", "forbidden_tool"}


def test_b_shared_path_is_read_only_allow_list_entry(tmp_path: Path) -> None:
    config = _config()
    environment = _make_environment(tmp_path, "B", config, include_producer=True)
    environment.consumer_workspace.mkdir(parents=True)
    shared = environment.root / "shared-artifact" / "handoff.json"
    shared.parent.mkdir(parents=True)
    shared.write_text("{}", encoding="utf-8")
    read_receipt = _scope_trace(
        [{"name": "read_file", "arguments": {"path": str(shared)}}],
        active_task_id="consumer-task",
        environment=environment,
        config=config,
        shared_artifact=shared,
    )
    assert read_receipt["ok"] is True
    write_receipt = _scope_trace(
        [{"name": "write_file", "arguments": {"path": str(shared)}}],
        active_task_id="consumer-task",
        environment=environment,
        config=config,
        shared_artifact=shared,
    )
    assert write_receipt["ok"] is False
    assert any(
        row["reason"] == "shared_artifact_mutation"
        for row in write_receipt["violations"]
    )


def test_v4a_patch_targets_are_all_scope_checked(tmp_path: Path) -> None:
    config = _config()
    environment = _make_environment(tmp_path, "A", config)
    environment.consumer_workspace.mkdir(parents=True)
    trace = [
        {
            "name": "patch",
            "arguments": {
                "mode": "patch",
                "patch": (
                    "*** Begin Patch\n"
                    "*** Update File: allowed.txt\n"
                    "@@\n-old\n+new\n"
                    f"*** Add File: {environment.root / 'outside.txt'}\n"
                    "+escaped\n"
                    "*** End Patch"
                ),
            },
        }
    ]
    receipt = _scope_trace(
        trace,
        active_task_id="consumer-task",
        environment=environment,
        config=config,
        shared_artifact=None,
    )
    assert receipt["ok"] is False
    assert [row["reason"] for row in receipt["violations"]] == ["outside_allow_list"]
    assert len(receipt["resolved_paths"]) == 2


def test_v4a_patch_without_headers_is_unresolvable(tmp_path: Path) -> None:
    config = _config()
    environment = _make_environment(tmp_path, "A", config)
    receipt = _scope_trace(
        [{"name": "patch", "arguments": {"mode": "patch", "patch": "garbage"}}],
        active_task_id="consumer-task",
        environment=environment,
        config=config,
        shared_artifact=None,
    )
    assert receipt["ok"] is False
    assert receipt["violations"] == [
        {"tool": "patch", "reason": "unresolvable_patch_targets"}
    ]


def test_scratchpad_receipt_hashes_actual_readback(monkeypatch) -> None:
    class CorruptingStore(WorkflowContextStore):
        def view(self, workflow_id, *, declared_reads):
            real = super().view(workflow_id, declared_reads=declared_reads)

            class CorruptingView:
                @staticmethod
                def read(key):
                    value = real.read(key)
                    payload = b"{}"
                    return replace(
                        value,
                        payload=payload,
                        sha256=digest_bytes(payload),
                    )

            return CorruptingView()

    monkeypatch.setattr(runtime_v2, "WorkflowContextStore", CorruptingStore)
    _text, receipts, exact = _scratchpad_projection(TASKS_BY_ID["artifact_policy_join"])
    assert exact is False
    assert receipts[-1] == {
        "hop": "scratchpad_readback",
        "byte_count": 2,
        "sha256": digest_bytes(b"{}"),
    }


def test_explicit_foreign_kanban_id_is_scope_expansion(tmp_path: Path) -> None:
    config = _config()
    environment = _make_environment(tmp_path, "C", config)
    receipt = _scope_trace(
        [{"name": "kanban_show", "arguments": {"task_id": "producer-task"}}],
        active_task_id="consumer-task",
        environment=environment,
        config=config,
        shared_artifact=None,
    )
    assert receipt["ok"] is False
    assert receipt["violations"] == [
        {"tool": "kanban_show", "reason": "foreign_task_id"}
    ]
