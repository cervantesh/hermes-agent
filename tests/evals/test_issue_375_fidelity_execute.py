import json
from pathlib import Path

import pytest

from evals.issue_375_fidelity_research.execute_lane_r import (
    _authorization,
    _pilot_can_continue,
    _public_summary,
    _validate_stage_inputs,
)
from evals.issue_375_fidelity_research.provider import UsageBudget
from evals.issue_375_fidelity_research.runner import (
    JudgeOutputFormatError,
    JudgeScoreRangeError,
    PairStore,
)


def _budget() -> UsageBudget:
    return UsageBudget(1700, 5100, 3_000_000, 1_500_000, 5.0)


def _store(
    tmp_path, *, completed: int, causes: list[str]
) -> tuple[PairStore, list[str]]:
    store = PairStore(tmp_path)
    task_ids = [f"task-{index:02d}" for index in range(completed + len(causes))]
    for task_id in task_ids[:completed]:
        assert store.begin(task_id)
        store.complete(task_id, {"status": "COMPLETE"}, {"status": "COMPLETE"})
    for task_id, cause in zip(task_ids[completed:], causes, strict=True):
        assert store.begin(task_id)
        receipt = {
            "status": "QUARANTINED_RUNTIME_FAILURE",
            "phase": "judging",
            "cause_type": cause,
        }
        store.complete(task_id, receipt, receipt)
    return store, task_ids


def test_r2_pilot_passes_with_eighteen_complete_and_two_typed_judge_quarantines(
    tmp_path,
):
    store, task_ids = _store(
        tmp_path,
        completed=18,
        causes=["JudgeOutputFormatError", "JudgeScoreRangeError"],
    )

    summary = _public_summary(store, task_ids, _budget(), "pilot")

    assert summary["conformance_pass"] is True
    assert summary["status"] == "COMPLETE_WITH_ALLOWED_QUARANTINE"
    assert summary["allowed_content_quarantines"] == 2
    assert summary["disallowed_quarantines"] == 0
    assert "wins" not in summary


def test_r2_pilot_rejects_any_non_judge_quarantine(tmp_path):
    store, task_ids = _store(tmp_path, completed=19, causes=["TimeoutError"])

    summary = _public_summary(store, task_ids, _budget(), "pilot")

    assert summary["conformance_pass"] is False
    assert summary["disallowed_quarantines"] == 1


def test_r2_pilot_continues_only_after_typed_judge_output_quarantine():
    assert (
        _pilot_can_continue(
            JudgeOutputFormatError("bad format"), allowed_quarantine_count=1
        )
        is True
    )
    assert (
        _pilot_can_continue(
            JudgeScoreRangeError("bad range"), allowed_quarantine_count=2
        )
        is True
    )
    assert (
        _pilot_can_continue(
            JudgeOutputFormatError("third violation"), allowed_quarantine_count=3
        )
        is False
    )
    assert (
        _pilot_can_continue(ValueError("other failure"), allowed_quarantine_count=1)
        is False
    )


def test_r2_pilot_accepts_only_the_sealed_disjoint_manifest_and_schedule(tmp_path):
    root = Path(__file__).parents[2] / "evals" / "issue_375_fidelity_research"
    frozen = root / "frozen_inputs"
    _validate_stage_inputs(
        root=root,
        stage="pilot",
        manifest_path=frozen / "PILOT_R2_MANIFEST.json",
        schedule_path=frozen / "PILOT_R2_SCHEDULE.json",
    )

    tampered = tmp_path / "manifest.json"
    payload = json.loads((frozen / "PILOT_R2_MANIFEST.json").read_text())
    payload["seed"] = "post-observation-seed"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="sealed stage inputs"):
        _validate_stage_inputs(
            root=root,
            stage="pilot",
            manifest_path=tampered,
            schedule_path=frozen / "PILOT_R2_SCHEDULE.json",
        )


def test_r1_authorization_cannot_unlock_r2_provider_execution(tmp_path):
    authorization = {
        "approved": True,
        "protocol_id": "IP375-FIDELITY-EXECUTION-R1-2026-09-03",
        "protocol_sha256": (
            "78294319621e91540173c2dc19b01eb3b698f70c735cbe7a44ea40b3a5310305"
        ),
        "stage": "pilot",
        "generation_and_extraction_model": "claude-haiku-4-5-20251001",
        "judge_model": "claude-sonnet-4-5-20250929",
        "limits": {
            "max_logical_calls": 340,
            "max_transport_attempts": 1020,
            "max_input_tokens": 2_000_000,
            "max_output_tokens": 1_500_000,
            "max_cost_usd": 10.0,
        },
    }
    path = tmp_path / "RUN_AUTHORIZATION.json"
    path.write_text(json.dumps(authorization), encoding="utf-8")

    with pytest.raises(ValueError, match="does not match the frozen stage"):
        _authorization(path, "pilot")
