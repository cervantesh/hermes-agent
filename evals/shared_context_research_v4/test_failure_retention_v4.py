from __future__ import annotations

import argparse
import json
from types import SimpleNamespace

import pytest

from evals.shared_context_research_v4.fixture_worker_v4 import _failure_record
from evals.shared_context_research_v4.protocol_v4 import COHORTS
from evals.shared_context_research_v4.runner_v4 import (
    _record_inflight,
    _record_protocol_abort,
    _refuse_aborted,
    _resolve_or_refuse_inflight,
    _run_fixture,
)
from evals.shared_context_research_v4.sanitize_v4 import sanitize_fixture_v4


def test_non_provider_timeout_is_a_safe_fixture_failure() -> None:
    args = argparse.Namespace(
        task="ordered_dependency_plan", schedule_seed=377, preflight=False
    )

    record = _failure_record(args, TimeoutError("consumer private-id did not finish"))

    assert record["provider_failure"] is None
    assert record["fixture_failure"]["exception_type"] == "TimeoutError"
    assert record["fixture_failure"]["failure_phase"] == "fixture_execution"
    assert len(record["fixture_failure"]["message_sha256"]) == 64
    assert "private-id" not in json.dumps(record["fixture_failure"])
    assert "private-id" in record["private_exception"]
    assert record["topology"] == "detached_source"
    assert set(record["order"]) == {"A", "B", "C"}

    record.update({
        "cohort": "sonnet-s377",
        "model": "claude-sonnet-4-6",
        "provider": "claude-code",
        "attempts": 1,
        "protocol_sha256": "a" * 64,
        "source_manifest_sha256": "b" * 64,
        "remote_seal_source_commit": "c" * 40,
        "run_started_at_utc": "2026-09-02T03:00:00Z",
        "target_head": "d" * 40,
        "target_dirty": False,
    })
    public = sanitize_fixture_v4(record)
    assert public["fixture_failure"] == record["fixture_failure"]
    assert "private_exception" not in public


def test_runner_retains_code_three_without_retry(monkeypatch, tmp_path) -> None:
    payload = {
        "task": "ordered_dependency_plan",
        "schedule_seed": 377,
        "provider_failure": None,
        "fixture_failure": {
            "exception_type": "TimeoutError",
            "failure_phase": "fixture_execution",
            "message_sha256": "a" * 64,
        },
        "arms": {},
        "integrity": {},
    }
    calls = []

    def fake_run(*_args, **_kwargs):
        calls.append(1)
        return SimpleNamespace(
            returncode=3, stdout=json.dumps(payload) + "\n", stderr=""
        )

    monkeypatch.setattr("subprocess.run", fake_run)
    args = SimpleNamespace(repo_root=tmp_path, python_executable=tmp_path / "python")

    record, attempts = _run_fixture(args, COHORTS[0], "ordered_dependency_plan")

    assert record == payload
    assert attempts == 1
    assert len(calls) == 1


def test_worker_protocol_abort_permanently_blocks_resume(tmp_path) -> None:
    output = tmp_path / "label" / "raw-v4.jsonl"
    _record_protocol_abort(
        output,
        cohort="sonnet-s377",
        task="ordered_dependency_plan",
        source_manifest_sha256="a" * 64,
        exc=RuntimeError("private protocol detail"),
    )

    marker = json.loads((output.parent / "ABORTED.json").read_text())
    assert marker["status"] == "permanently_aborted"
    assert "private protocol detail" not in json.dumps(marker)
    with pytest.raises(RuntimeError, match="permanently aborted"):
        _refuse_aborted(output)


def test_unresolved_inflight_slot_cannot_be_replaced(tmp_path) -> None:
    output = tmp_path / "label" / "raw-v4.jsonl"
    output.parent.mkdir(parents=True)
    _record_inflight(
        output,
        cohort="sonnet-s377",
        task="ordered_dependency_plan",
        source_manifest_sha256="a" * 64,
    )
    with pytest.raises(RuntimeError, match="unresolved inflight"):
        _resolve_or_refuse_inflight(output, [])

    _resolve_or_refuse_inflight(
        output,
        [{"cohort": "sonnet-s377", "task": "ordered_dependency_plan"}],
    )
    assert not (output.parent / "INFLIGHT.json").exists()
