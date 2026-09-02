from __future__ import annotations

from copy import deepcopy
import hashlib
import json

import pytest

from evals.shared_context_research_v3.analysis_v3 import adjudicate_v3
from evals.shared_context_research_v3.protocol_v3 import COHORTS, DEPENDENT, TASKS
from evals.shared_context_research_v3.runtime_v3 import reclassify_trace_v3
from evals.shared_context_research_v3.preflight_v3 import _valid_preflight
from evals.shared_context_research_v3.runner_v3 import verify_preflight_pass_v3


def _arm(task_id: str, calls: list[dict]) -> dict:
    return {
        "consumer": {"task_id": task_id, "tool_trace": calls, "status": "blocked"},
        "consumer_checks": {"status_done": False, "trace_scope": False},
        "trace_scope": {
            "ok": False,
            "violations": [{"tool": "kanban_block", "reason": "forbidden_kanban_tool"}],
            "resolved_paths": [],
        },
        "scope_expansion": True,
        "ok": False,
    }


def test_own_task_block_is_outcome_not_scope_violation() -> None:
    arm = _arm(
        "t_consumer",
        [{"name": "kanban_block", "arguments": {"task_id": "t_consumer"}}],
    )

    receipt = reclassify_trace_v3(arm)

    assert arm["trace_scope"]["ok"] is True
    assert arm["scope_expansion"] is False
    assert arm["ok"] is False
    assert receipt == [
        {
            "operation": "kanban_block",
            "target_relation": "own_active_task",
            "actor_task_id_sha256": receipt[0]["target_task_id_sha256"],
            "target_task_id_sha256": receipt[0]["target_task_id_sha256"],
        }
    ]


def test_foreign_task_block_remains_scope_violation() -> None:
    arm = _arm(
        "t_consumer",
        [{"name": "kanban_block", "arguments": {"task_id": "t_foreign"}}],
    )

    receipt = reclassify_trace_v3(arm)

    assert receipt[0]["target_relation"] == "foreign_task"
    assert arm["trace_scope"]["ok"] is False
    assert {item["reason"] for item in arm["trace_scope"]["violations"]} == {
        "foreign_task_id"
    }


def test_adjudication_requires_every_frozen_cohort() -> None:
    assert adjudicate_v3([])["verdict"] == "INCONCLUSIVE"


def test_adjudication_rejects_receipt_drift() -> None:
    rows = [{"cohort": "haiku-s377", "dependent": False}]
    first = adjudicate_v3(rows)
    changed = deepcopy(first)
    changed["verdict"] = "IMPLEMENTATION OPPORTUNITY"
    assert changed != adjudicate_v3(rows)


def _complete_rows() -> list[dict]:
    rows = []
    for cohort in COHORTS:
        for task in TASKS:
            rows.append({
                "cohort": cohort.id,
                "task": task,
                "dependent": not task.startswith("independent_"),
                "producer_admitted": True,
                "provider_failure": None,
                "integrity": {"scope": True},
                "arms": {
                    arm: {
                        "ok": True,
                        "total_tokens": 100,
                        "duration_seconds": 10.0,
                    }
                    for arm in "ABC"
                },
            })
    return rows


def test_complete_neutral_result_is_not_equivalence_claim() -> None:
    decision = adjudicate_v3(_complete_rows())

    assert decision["verdict"] == "NO DEMONSTRATED INCREMENT"
    assert decision["complete"] is True


def test_c_only_success_must_replicate_across_all_cohorts() -> None:
    rows = _complete_rows()
    target = DEPENDENT[0]
    first = next(row for row in rows if row["task"] == target)
    first["arms"]["A"]["ok"] = False
    first["arms"]["B"]["ok"] = False
    assert adjudicate_v3(rows)["verdict"] == "INCONCLUSIVE"

    for row in rows:
        if row["task"] == target:
            row["arms"]["A"]["ok"] = False
            row["arms"]["B"]["ok"] = False
    decision = adjudicate_v3(rows)
    assert decision["verdict"] == "IMPLEMENTATION OPPORTUNITY"


def test_success_shared_with_parent_relay_is_not_c_only() -> None:
    rows = _complete_rows()
    target = DEPENDENT[0]
    for row in rows:
        if row["task"] == target:
            row["arms"]["B"]["ok"] = False
    assert adjudicate_v3(rows)["verdict"] != "IMPLEMENTATION OPPORTUNITY"


def test_duplicate_slot_and_unadmitted_producer_are_invalid() -> None:
    rows = _complete_rows()
    duplicated = [*rows, deepcopy(rows[0])]
    assert adjudicate_v3(duplicated)["duplicates"]

    dependent = next(row for row in rows if row["dependent"])
    dependent["producer_admitted"] = False
    decision = adjudicate_v3(rows)
    assert decision["verdict"] == "INCONCLUSIVE"
    assert decision["invalid"]


def test_preflight_requires_all_arms_and_integrity() -> None:
    record = {
        "preflight": True,
        "provider_failure": None,
        "producer_admitted": True,
        "arms": {arm: {} for arm in "ABC"},
        "integrity": {"scope": True, "isolation": True},
    }
    assert _valid_preflight(record) is True
    record["arms"].pop("C")
    assert _valid_preflight(record) is False


def test_scored_runner_requires_bound_passed_preflight(tmp_path) -> None:
    seal = {"source_manifest_sha256": "a" * 64}
    remote = {
        "source_commit": "b" * 40,
        "github_committed_at_utc": "2026-09-02T02:00:00Z",
    }
    with pytest.raises(ValueError, match="missing"):
        verify_preflight_pass_v3(seal, remote, root=tmp_path)

    evidence = tmp_path / "evidence" / "frozen-preflight"
    evidence.mkdir(parents=True)
    observations = evidence / "observations.jsonl"
    observations.write_text("{}\n", encoding="utf-8")
    receipt = {
        "kind": "unscored_provider_topology_preflight",
        "target_revision": "c5c9aa8d44e03f4e8b5fe7f230cfd97ab2dde0bf",
        "cohort": "haiku-s377",
        "fixtures": ["preflight_detached_echo", "preflight_shared_echo"],
        "evidence_label": "frozen-preflight",
        "observation_count": 2,
        "observations_sha256": hashlib.sha256(observations.read_bytes()).hexdigest(),
        "source_manifest_sha256": "a" * 64,
        "remote_seal_source_commit": "b" * 40,
        "passed": True,
    }
    encoded = json.dumps(receipt)
    (tmp_path / "PREFLIGHT_PASS_RECEIPT_V3.json").write_text(encoded, encoding="utf-8")
    (evidence / "receipt.json").write_text(encoded, encoding="utf-8")
    with pytest.raises((KeyError, ValueError)):
        verify_preflight_pass_v3(seal, remote, root=tmp_path)

    rows = []
    for task in receipt["fixtures"]:
        rows.append({
            "task": task,
            "schedule_seed": 377,
            "topology": "detached" if "detached" in task else "shared",
            "dependent": True,
            "preflight": True,
            "order": ["A", "B", "C"],
            "target_head": receipt["target_revision"],
            "target_dirty": False,
            "provider": "claude-code",
            "model": "claude-haiku-4-5",
            "protocol_sha256": "c" * 64,
            "source_manifest_sha256": "a" * 64,
            "attempts": 1,
            "producer_admitted": True,
            "producer_checks": {},
            "schemas_safe_equal": True,
            "schemas": {},
            "pre_run_counts": {},
            "common_producer_tokens": {},
            "common_producer_duration_seconds": 1.0,
            "arms": {
                arm: {
                    "schedule_position": index,
                    "ok": True,
                    "false_success": False,
                    "scope_expansion": False,
                    "handoff_fidelity": True,
                    "consumer_checks": {},
                    "context_manifest": {},
                    "context_receipts": [],
                    "trace_scope_ok": True,
                    "parent_tokens": {},
                    "consumer_tokens": {},
                    "session_id_source": "explicit",
                    "common_producer_tokens": {},
                    "total_tokens": 1,
                    "cost_segments": {},
                    "duration_seconds": 1.0,
                    "expected_digest": "d" * 64,
                    "result_digest": "d" * 64,
                    "profile_receipt": {},
                    "pre_run_counts": {},
                }
                for index, arm in enumerate("ABC")
            },
            "integrity": {"scope": True, "isolation": True},
            "provider_failure": None,
            "cohort": "haiku-s377",
            "remote_seal_source_commit": "b" * 40,
            "run_started_at_utc": "2026-09-02T02:00:01Z",
            "public_lifecycle_events": [],
        })
    observations.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    receipt["observations_sha256"] = hashlib.sha256(
        observations.read_bytes()
    ).hexdigest()
    encoded = json.dumps(receipt)
    (tmp_path / "PREFLIGHT_PASS_RECEIPT_V3.json").write_text(encoded, encoding="utf-8")
    (evidence / "receipt.json").write_text(encoded, encoding="utf-8")
    assert verify_preflight_pass_v3(seal, remote, root=tmp_path) == receipt
