import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from evals.issue_375_fidelity_research.calibration import CalibrationStore
from evals.issue_375_fidelity_research.execute_calibration_r4 import (
    CONTROL_JUDGE_MODEL,
    FIDELITY_JUDGE_MODEL,
    GENERATOR_MODEL,
    LIMITS,
    PROTOCOL_ID,
    PROTOCOL_SHA256,
    DeadlineBackend,
    DeadlineExceeded,
    FidelityJudgeUnavailable,
    _authorization,
    _bind_run_identity,
    _control_status,
    _run_track,
    _usage_is_lower_bound,
    _run_sequential_tracks,
    _validate_protocol,
    _validate_inputs,
    _verify_model_metadata,
    _write_summary,
)
from evals.issue_375_fidelity_research.freeze_r4_inputs import generate
from evals.issue_375_fidelity_research.provider import UsageBudget


def _write_dataset(path, count=220):
    records = [
        {
            "id": f"{index:03d}",
            "original_task": f"Original task {index}",
            "specified_task": f"Specified task {index}",
            "role_1": "Programmer_RoleType.ASSISTANT",
            "role_2": "Filmmaker_RoleType.USER",
        }
        for index in range(count)
    ]
    path.write_text(json.dumps(records), encoding="utf-8")


def _manifest(path, ids):
    path.write_text(
        json.dumps({"records": [{"id": task_id} for task_id in ids]}),
        encoding="utf-8",
    )


def test_r4_cohort_is_fresh_and_seal_binds_dataset(tmp_path):
    dataset = tmp_path / "dataset.json"
    _write_dataset(dataset)
    exclusions = []
    for name, ids in (
        ("scored", range(100)),
        ("r2", range(100, 120)),
        ("r3", range(120, 150)),
    ):
        path = tmp_path / f"{name}.json"
        _manifest(path, [f"{index:03d}" for index in ids])
        exclusions.append(path)

    first = generate(
        output_dir=tmp_path / "first",
        dataset_path=dataset,
        exclusion_manifests=exclusions,
    )
    second = generate(
        output_dir=tmp_path / "second",
        dataset_path=dataset,
        exclusion_manifests=exclusions,
    )

    assert first == second
    manifest = json.loads((tmp_path / "first" / "R4_MANIFEST.json").read_text())
    schedule = json.loads((tmp_path / "first" / "R4_SCHEDULE.json").read_text())
    assert {record["id"] for record in manifest["records"]}.isdisjoint({
        f"{index:03d}" for index in range(150)
    })
    assert len(manifest["records"]) == 30
    assert all(row["order_reversal"] for row in schedule)
    assert first["dataset_sha256"]
    assert first["excluded_id_count"] == 150


def test_r4_validates_only_its_sealed_inputs():
    root = Path(__file__).parents[2] / "evals" / "issue_375_fidelity_research"
    frozen = root / "frozen_inputs"
    digest = _validate_inputs(
        root=root,
        manifest_path=frozen / "R4_MANIFEST.json",
        schedule_path=frozen / "R4_SCHEDULE.json",
    )
    assert len(digest) == 64


def test_r4_protocol_seal_is_validated(tmp_path):
    source = Path(__file__).parents[2] / "evals" / "issue_375_fidelity_research"
    root = tmp_path / "research"
    root.mkdir()
    for name in ("JUDGE_CALIBRATION_R4_FREEZE.md", "JUDGE_CALIBRATION_R4_SEAL.json"):
        (root / name).write_bytes((source / name).read_bytes())
    _validate_protocol(root)
    (root / "JUDGE_CALIBRATION_R4_FREEZE.md").write_text("mutated", encoding="utf-8")
    with pytest.raises(ValueError, match="protocol artifact"):
        _validate_protocol(root)


def _auth(input_sha, harness_commit):
    return {
        "approved": True,
        "protocol_id": PROTOCOL_ID,
        "protocol_sha256": PROTOCOL_SHA256,
        "inputs_seal_sha256": input_sha,
        "harness_commit": harness_commit,
        "generation_and_extraction_provider": "anthropic",
        "generation_and_extraction_model": GENERATOR_MODEL,
        "fidelity_judge_provider": "openai",
        "fidelity_judge_model": FIDELITY_JUDGE_MODEL,
        "control_judge_provider": "anthropic",
        "control_judge_model": CONTROL_JUDGE_MODEL,
        "limits": LIMITS,
    }


def test_r4_requires_new_authorization_bound_to_harness_and_providers(tmp_path):
    input_sha = "a" * 64
    harness = "b" * 40
    path = tmp_path / "R4_RUN_AUTHORIZATION.json"
    path.write_text(json.dumps(_auth(input_sha, harness)), encoding="utf-8")
    assert _authorization(path, input_sha, harness)["approved"] is True

    stale = _auth(input_sha, harness)
    stale["protocol_id"] = "IP375-JUDGE-CALIBRATION-R3-2026-09-03"
    path.write_text(json.dumps(stale), encoding="utf-8")
    with pytest.raises(ValueError, match="frozen R4"):
        _authorization(path, input_sha, harness)

    with_secret = _auth(input_sha, harness)
    with_secret["api_key"] = "must-not-be-accepted"
    path.write_text(json.dumps(with_secret), encoding="utf-8")
    with pytest.raises(ValueError, match="frozen R4"):
        _authorization(path, input_sha, harness)


def test_run_identity_rejects_stale_or_unbound_output_roots(tmp_path):
    expected = {
        "protocol_id": PROTOCOL_ID,
        "protocol_sha256": PROTOCOL_SHA256,
        "inputs_seal_sha256": "a" * 64,
        "harness_commit": "b" * 40,
        "source_digests": {"dataset": "c" * 64},
        "providers": {"generation": "anthropic"},
        "models": {"generation": GENERATOR_MODEL},
        "limits": LIMITS,
    }
    root = tmp_path / "fresh"
    first = _bind_run_identity(root, expected, now=100.0)
    second = _bind_run_identity(root, expected, now=999.0)
    assert first == second
    assert first["started_at_epoch"] == 100.0

    changed = json.loads(json.dumps(expected))
    changed["harness_commit"] = "d" * 40
    with pytest.raises(ValueError, match="different evidence frame"):
        _bind_run_identity(root, changed, now=1000.0)

    identity_path = root / "R4_RUN_IDENTITY.json"
    tampered = json.loads(identity_path.read_text(encoding="utf-8"))
    tampered["deadline_epoch"] += 1
    identity_path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(ValueError, match="different evidence frame"):
        _bind_run_identity(root, expected, now=1000.0)

    stale = tmp_path / "stale"
    stale.mkdir()
    (stale / "R4_BUDGET_STATE.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="unbound output root"):
        _bind_run_identity(stale, expected, now=100.0)


class _CountingBackend:
    def __init__(self):
        self.calls = 0

    def complete(self, **kwargs):
        self.calls += 1
        return "ok"


def test_deadline_is_checked_before_every_dispatch():
    backend = _CountingBackend()
    guarded = DeadlineBackend(backend, deadline_epoch=10.0, clock=lambda: 11.0)
    with pytest.raises(DeadlineExceeded):
        guarded.complete()
    assert backend.calls == 0


def test_deadline_guard_blocks_an_internal_retry_after_time_advances():
    now = [0.0]

    class RetryingBackend:
        def __init__(self):
            self.before_attempt = None
            self.receipts = []
            self.calls = 0

        def complete(self, **kwargs):
            self.before_attempt()
            self.calls += 1
            now[0] = 11.0
            self.before_attempt()
            self.calls += 1

    backend = RetryingBackend()
    guarded = DeadlineBackend(backend, deadline_epoch=10.0, clock=lambda: now[0])
    with pytest.raises(DeadlineExceeded):
        guarded.complete()
    assert backend.calls == 1


def test_fidelity_metadata_unavailability_has_a_typed_terminal_cause(tmp_path):
    openai_client = SimpleNamespace(
        models=SimpleNamespace(
            retrieve=lambda _model: (_ for _ in ()).throw(RuntimeError("unavailable"))
        )
    )
    with pytest.raises(FidelityJudgeUnavailable):
        _verify_model_metadata(
            openai_client,
            SimpleNamespace(),
            deadline_epoch=10.0,
            clock=lambda: 0.0,
        )

    path = tmp_path / "R4_PUBLIC_SUMMARY.json"
    summary = _write_summary(
        path=path,
        store=CalibrationStore(tmp_path / "store"),
        task_ids=[str(index) for index in range(30)],
        ready=0,
        budget=UsageBudget(10, 30, 1000, 1000, 1.0),
        primary_terminal={
            "status": "MODEL_METADATA_UNAVAILABLE",
            "cause_type": "FidelityJudgeUnavailable",
        },
        control_ran=False,
    )
    assert summary["disposition"] == "INCONCLUSIVE_FIDELITY_JUDGE_UNAVAILABLE"
    assert json.loads(path.read_text(encoding="utf-8")) == summary


def test_completed_summary_propagates_unknown_usage_from_successful_retry(tmp_path):
    path = tmp_path / "R4_PUBLIC_SUMMARY.json"
    backend = SimpleNamespace(
        receipts=[
            {
                "returned_model": GENERATOR_MODEL,
                "usage_unknown": True,
            }
        ]
    )

    summary = _write_summary(
        path=path,
        store=CalibrationStore(tmp_path / "store"),
        task_ids=[str(index) for index in range(30)],
        ready=30,
        budget=UsageBudget(10, 30, 1000, 1000, 1.0),
        primary_terminal=None,
        control_ran=True,
        transport_backends=(backend,),
    )

    assert summary["usage_is_lower_bound"] is True
    assert json.loads(path.read_text(encoding="utf-8")) == summary


def test_completed_summary_recovers_unknown_usage_from_durable_fixture(tmp_path):
    path = tmp_path / "R4_PUBLIC_SUMMARY.json"
    store = CalibrationStore(tmp_path / "store")
    task_ids = [str(index) for index in range(30)]
    store.finish_fixture(
        task_id=task_ids[0],
        private={"status": "JUDGE_READY"},
        public={
            "status": "JUDGE_READY",
            "arms": {
                "original": {
                    "generation_receipts": [{"usage_unknown": True}],
                    "extraction_receipts": [],
                }
            },
        },
    )

    summary = _write_summary(
        path=path,
        store=store,
        task_ids=task_ids,
        ready=30,
        budget=UsageBudget(10, 30, 1000, 1000, 1.0),
        primary_terminal=None,
        control_ran=True,
    )

    assert summary["usage_is_lower_bound"] is True
    assert json.loads(path.read_text(encoding="utf-8")) == summary


class _Store:
    def __init__(self):
        self.outcomes = {}

    def load_judgment_private(self, task_id, track, order):
        return {"mapped_outcome": self.outcomes[(task_id, order)]}

    def load_fixture_private(self, task_id):
        return {"solutions": {"original": "one", "ablated": "two"}}


def test_fidelity_track_stops_before_control_and_when_threshold_is_impossible(
    monkeypatch,
):
    calls = []
    store = _Store()

    def evaluate(**kwargs):
        task_id = kwargs["task_id"]
        track = kwargs["track"]
        order = kwargs["order"]
        calls.append((track, task_id, order))
        # First four pairs disagree, making 27/30 impossible.
        store.outcomes[(task_id, order)] = order
        return {"status": "COMPLETE"}

    monkeypatch.setattr(
        "evals.issue_375_fidelity_research.execute_calibration_r4.evaluate_judgment",
        evaluate,
    )
    tasks = [{"id": str(index), "specified_task": "task"} for index in range(30)]
    schedules = {task["id"]: {"judge_order": ["original", "ablated"]} for task in tasks}

    result = _run_track(
        tasks=tasks,
        schedules=schedules,
        store=store,
        sources=SimpleNamespace(evaluation_system="system"),
        judge=object(),
        track="fidelity",
        render_prompt=lambda *_: "prompt",
    )

    assert result["status"] == "REVERSAL_THRESHOLD_UNREACHABLE"
    assert len(calls) == 8
    assert {track for track, _, _ in calls} == {"fidelity"}


def test_track_stops_immediately_on_terminal_receipt(monkeypatch):
    calls = []

    def evaluate(**kwargs):
        calls.append((kwargs["task_id"], kwargs["order"]))
        return {"status": "QUARANTINED_UNKNOWN_PROVIDER_OUTCOME"}

    monkeypatch.setattr(
        "evals.issue_375_fidelity_research.execute_calibration_r4.evaluate_judgment",
        evaluate,
    )
    tasks = [
        {"id": "one", "specified_task": "task"},
        {"id": "two", "specified_task": "task"},
    ]
    schedules = {task["id"]: {"judge_order": ["original", "ablated"]} for task in tasks}
    result = _run_track(
        tasks=tasks,
        schedules=schedules,
        store=_Store(),
        sources=SimpleNamespace(evaluation_system="system"),
        judge=object(),
        track="fidelity",
        render_prompt=lambda *_: "prompt",
    )
    assert result["status"] == "QUARANTINED_UNKNOWN_PROVIDER_OUTCOME"
    assert calls == [("one", "forward")]


def test_control_status_has_frozen_executable_predicate():
    passing = {
        "complete_judgments": 60,
        "invalid_judgments": 0,
        "model_identity_failures": 0,
        "reversal_agreements": 27,
        "reversal_pairs": 30,
    }
    assert _control_status(passing, ran=True) == "PASS"
    failing = dict(passing, reversal_agreements=26)
    assert _control_status(failing, ran=True) == "NONCONFORMANT"
    assert _control_status({}, ran=False) == "NOT_RUN"


def test_unknown_transport_outcome_marks_usage_as_a_lower_bound():
    assert _usage_is_lower_bound({
        "status": "QUARANTINED_JUDGE_TRANSPORT_OR_IDENTITY",
        "cause_type": "TimeoutError",
        "transport_receipts": [],
    })
    assert not _usage_is_lower_bound({
        "status": "QUARANTINED_JUDGE_TRANSPORT_OR_IDENTITY",
        "cause_type": "DeadlineExceeded",
        "transport_receipts": [],
    })


def test_r4_connection_failure_is_lower_bound_even_with_earlier_success_receipts():
    assert _usage_is_lower_bound({
        "status": "QUARANTINED_FIXTURE_FAILURE",
        "cause_type": "APIConnectionError",
        "transport_receipts": [
            {"returned_model": GENERATOR_MODEL, "usage_unknown": False}
            for _ in range(6)
        ],
    })


def test_receipt_flag_marks_usage_as_lower_bound():
    assert _usage_is_lower_bound({
        "status": "QUARANTINED_FIXTURE_FAILURE",
        "cause_type": "RuntimeError",
        "transport_receipts": [{"usage_unknown": True}],
    })


def test_control_track_cannot_start_before_fidelity_pass(monkeypatch):
    calls = []

    def run_track(**kwargs):
        calls.append(kwargs["track"])
        return {"status": "QUARANTINED_JUDGE_SCORE_RANGE"}

    monkeypatch.setattr(
        "evals.issue_375_fidelity_research.execute_calibration_r4._run_track",
        run_track,
    )
    monkeypatch.setattr(
        "evals.issue_375_fidelity_research.execute_calibration_r4.summarize_calibration",
        lambda **_: {
            "tracks": {
                "fidelity": {
                    "complete_judgments": 0,
                    "invalid_judgments": 60,
                    "model_identity_failures": 0,
                    "reversal_agreements": 0,
                    "reversal_pairs": 0,
                }
            }
        },
    )

    terminal, passed, control_terminal = _run_sequential_tracks(
        tasks=[{"id": "one"}],
        schedules={},
        store=object(),
        sources=object(),
        fidelity_judge=object(),
        control_judge=object(),
    )

    assert terminal["status"] == "QUARANTINED_JUDGE_SCORE_RANGE"
    assert passed is False
    assert control_terminal is None
    assert calls == ["fidelity"]


def test_control_track_starts_only_after_complete_fidelity_gate(monkeypatch):
    calls = []

    def run_track(**kwargs):
        calls.append(kwargs["track"])
        return {"status": "TRACK_COMPLETE"}

    monkeypatch.setattr(
        "evals.issue_375_fidelity_research.execute_calibration_r4._run_track",
        run_track,
    )
    monkeypatch.setattr(
        "evals.issue_375_fidelity_research.execute_calibration_r4.summarize_calibration",
        lambda **_: {
            "tracks": {
                "fidelity": {
                    "complete_judgments": 60,
                    "invalid_judgments": 0,
                    "model_identity_failures": 0,
                    "reversal_agreements": 27,
                    "reversal_pairs": 30,
                }
            }
        },
    )

    _, passed, control_terminal = _run_sequential_tracks(
        tasks=[{"id": "one"}],
        schedules={},
        store=object(),
        sources=object(),
        fidelity_judge=object(),
        control_judge=object(),
    )

    assert passed is True
    assert control_terminal == {"status": "TRACK_COMPLETE"}
    assert calls == ["fidelity", "control"]


def test_control_unknown_outcome_is_propagated_for_lower_bound_accounting(monkeypatch):
    calls = []

    def run_track(**kwargs):
        calls.append(kwargs["track"])
        if kwargs["track"] == "fidelity":
            return {"status": "TRACK_COMPLETE"}
        return {
            "status": "QUARANTINED_JUDGE_TRANSPORT_OR_IDENTITY",
            "cause_type": "TimeoutError",
            "transport_receipts": [],
        }

    monkeypatch.setattr(
        "evals.issue_375_fidelity_research.execute_calibration_r4._run_track",
        run_track,
    )
    monkeypatch.setattr(
        "evals.issue_375_fidelity_research.execute_calibration_r4.summarize_calibration",
        lambda **_: {
            "tracks": {
                "fidelity": {
                    "complete_judgments": 60,
                    "invalid_judgments": 0,
                    "model_identity_failures": 0,
                    "reversal_agreements": 27,
                    "reversal_pairs": 30,
                }
            }
        },
    )

    _, passed, control_terminal = _run_sequential_tracks(
        tasks=[{"id": "one"}],
        schedules={},
        store=object(),
        sources=object(),
        fidelity_judge=object(),
        control_judge=object(),
    )

    assert passed is True
    assert _usage_is_lower_bound(control_terminal) is True
    assert calls == ["fidelity", "control"]
