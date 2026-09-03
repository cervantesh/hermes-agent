import json
from dataclasses import dataclass

from evals.issue_375_fidelity_research.calibration import (
    CalibrationStore,
    evaluate_judgment,
    prepare_and_checkpoint_fixture,
    summarize_calibration,
)
from evals.issue_375_fidelity_research.protocol import Generation
from evals.issue_375_fidelity_research.sources import PromptSources


@dataclass
class QueueBackend:
    outputs: list[str]
    model: str = "gpt-4-0613"

    def __post_init__(self):
        self.calls = 0
        self.receipts = []

    def complete(self, *, agent, system_prompt, messages, parameters):
        self.calls += 1
        text = self.outputs.pop(0)
        self.receipts.append({
            "agent": agent,
            "requested_model": self.model,
            "returned_model": self.model,
            "response_sha256": "transport-hash",
            "usage": {"input_tokens": 11, "output_tokens": 7},
            "attempts": 1,
            "latency_ms": 1.5,
        })
        return Generation(text=text, finish_reason="stop", usage={})


class FailIfCalled:
    receipts = []

    def complete(self, **kwargs):
        raise AssertionError("provider must not be called while resuming raw output")


class ReceiptedFailure:
    def __init__(self):
        self.receipts = []

    def complete(self, **kwargs):
        self.receipts.append({
            "requested_model": "claude-haiku-4-5-20251001",
            "returned_model": "claude-haiku-4-5-20251001",
            "response_sha256": "non-text-hash",
            "content_types": ["thinking"],
            "usage": {"input_tokens": 17, "output_tokens": 9},
            "attempts": 1,
        })
        raise ValueError("provider response contained no text block")


def _sources():
    return PromptSources(
        original_assistant="OA <ASSISTANT_ROLE> <USER_ROLE> <TASK>",
        original_user="OU <USER_ROLE> <ASSISTANT_ROLE> <TASK>",
        task_specifier="unused",
        ablated_assistant="AA <ASSISTANT_ROLE> <USER_ROLE> <TASK>",
        ablated_user="AU <USER_ROLE> <ASSISTANT_ROLE> <TASK>",
        solution_extraction="extract exactly",
        evaluation_system="judge exactly",
        evaluation_template="Q={question}\nA1={answer_1}\nA2={answer_2}\nP={prompt}",
        evaluation_instruction="score",
    )


def test_generation_and_extraction_checkpoint_precedes_judging_and_resumes(tmp_path):
    store = CalibrationStore(tmp_path)
    generator = QueueBackend([
        "hidden original",
        "<CAMEL_TASK_DONE>",
        "discarded original assistant",
        "hidden ablated",
        "<CAMEL_TASK_DONE>",
        "discarded ablated assistant",
    ])
    extractor = QueueBackend(["original solution", "ablated solution"])
    task = {
        "id": "task-1",
        "original_task": "original task",
        "specified_task": "specified task",
        "assistant_role": "Programmer",
        "user_role": "Filmmaker",
    }
    schedule = {
        "task_id": "task-1",
        "generation_order": ["original", "ablated"],
        "judge_order": ["original", "ablated"],
        "blind_labels": ["Assistant 1", "Assistant 2"],
        "order_reversal": True,
    }

    first = prepare_and_checkpoint_fixture(
        store=store,
        task=task,
        schedule=schedule,
        sources=_sources(),
        generator=generator,
        extractor=extractor,
    )
    second = prepare_and_checkpoint_fixture(
        store=store,
        task=task,
        schedule=schedule,
        sources=_sources(),
        generator=FailIfCalled(),
        extractor=FailIfCalled(),
    )

    assert first["status"] == second["status"] == "JUDGE_READY"
    private = store.load_fixture_private("task-1")
    public = store.load_fixture_public("task-1")
    assert private["solutions"] == {
        "original": "original solution",
        "ablated": "ablated solution",
    }
    serialized = json.dumps(public)
    assert "original solution" not in serialized
    assert "specified task" not in serialized
    assert public["status"] == "JUDGE_READY"


def test_started_fixture_without_checkpoint_becomes_unknown_not_retriable(tmp_path):
    store = CalibrationStore(tmp_path)
    assert store.begin_fixture("task-1") is True

    recovered = store.recover_interrupted_fixtures()

    assert recovered == [
        {
            "task_id": "task-1",
            "status": "QUARANTINED_UNKNOWN_PROVIDER_OUTCOME",
        }
    ]
    assert store.begin_fixture("task-1") is False


def test_fixture_failure_records_phase_arm_and_sanitized_transport(tmp_path):
    store = CalibrationStore(tmp_path)
    task = {
        "id": "task-1",
        "original_task": "original task",
        "specified_task": "specified task",
        "assistant_role": "Programmer",
        "user_role": "Filmmaker",
    }
    schedule = {
        "task_id": "task-1",
        "generation_order": ["original", "ablated"],
        "judge_order": ["original", "ablated"],
        "order_reversal": True,
    }

    result = prepare_and_checkpoint_fixture(
        store=store,
        task=task,
        schedule=schedule,
        sources=_sources(),
        generator=ReceiptedFailure(),
        extractor=FailIfCalled(),
    )

    assert result["status"] == "QUARANTINED_FIXTURE_FAILURE"
    assert result["phase"] == "generation"
    assert result["arm"] == "original"
    assert result["transport_receipts"][0]["content_types"] == ["thinking"]
    assert "specified task" not in json.dumps(result)


def test_range_failure_preserves_raw_and_numeric_pair_privately_only(tmp_path):
    store = CalibrationStore(tmp_path)
    backend = QueueBackend(["0 12\nprivate rationale"])

    result = evaluate_judgment(
        store=store,
        task_id="task-1",
        track="fidelity",
        order="forward",
        answer_order=["original", "ablated"],
        system_prompt="paper system",
        user_prompt="paper evaluation",
        backend=backend,
    )

    assert result["status"] == "QUARANTINED_JUDGE_SCORE_RANGE"
    private = store.load_judgment_private("task-1", "fidelity", "forward")
    public = store.load_judgment_public("task-1", "fidelity", "forward")
    assert private["raw_response"] == "0 12\nprivate rationale"
    assert private["unmapped_numeric_pair"] == [0.0, 12.0]
    serialized = json.dumps(public)
    assert "private rationale" not in serialized
    assert "0.0" not in serialized
    assert "12.0" not in serialized
    assert "original" not in serialized
    assert "ablated" not in serialized
    assert public["parse_category"] == "JudgeScoreRangeError"


def test_resume_parses_raw_checkpoint_without_repeating_provider_call(tmp_path):
    store = CalibrationStore(tmp_path)
    assert store.begin_judgment("task-1", "fidelity", "forward") is True
    store.persist_raw_judgment(
        task_id="task-1",
        track="fidelity",
        order="forward",
        answer_order=["original", "ablated"],
        raw_response="8 6\nreason",
        transport_receipts=[{"returned_model": "gpt-4-0613"}],
    )

    result = evaluate_judgment(
        store=store,
        task_id="task-1",
        track="fidelity",
        order="forward",
        answer_order=["original", "ablated"],
        system_prompt="paper system",
        user_prompt="paper evaluation",
        backend=FailIfCalled(),
    )

    assert result["status"] == "COMPLETE"
    private = store.load_judgment_private("task-1", "fidelity", "forward")
    assert private["mapped_outcome"] == "original"


def test_started_request_without_raw_response_becomes_unknown_not_retriable(tmp_path):
    store = CalibrationStore(tmp_path)
    assert store.begin_judgment("task-1", "fidelity", "forward") is True

    recovered = store.recover_interrupted_judgments()

    assert recovered == [
        {
            "task_id": "task-1",
            "track": "fidelity",
            "order": "forward",
            "status": "QUARANTINED_UNKNOWN_PROVIDER_OUTCOME",
        }
    ]
    assert store.begin_judgment("task-1", "fidelity", "forward") is False


def test_judge_failure_preserves_sanitized_transport_receipt(tmp_path):
    store = CalibrationStore(tmp_path)
    backend = ReceiptedFailure()

    result = evaluate_judgment(
        store=store,
        task_id="task-1",
        track="fidelity",
        order="forward",
        answer_order=["original", "ablated"],
        system_prompt="paper system",
        user_prompt="paper evaluation",
        backend=backend,
    )

    assert result["status"] == "QUARANTINED_JUDGE_TRANSPORT_OR_IDENTITY"
    assert result["transport_receipts"][0]["content_types"] == ["thinking"]
    assert "private" not in json.dumps(result)


def test_summary_exposes_only_conformance_and_reversal_agreement(tmp_path):
    store = CalibrationStore(tmp_path)
    for order, answer_order, response in (
        ("forward", ["original", "ablated"], "8 6\nreason"),
        ("reverse", ["ablated", "original"], "6 8\nreason"),
    ):
        evaluate_judgment(
            store=store,
            task_id="task-1",
            track="fidelity",
            order=order,
            answer_order=answer_order,
            system_prompt="paper system",
            user_prompt="paper evaluation",
            backend=QueueBackend([response]),
        )

    summary = summarize_calibration(
        store=store,
        task_ids=["task-1"],
        tracks=["fidelity"],
    )

    assert summary["tracks"]["fidelity"] == {
        "complete_judgments": 2,
        "invalid_judgments": 0,
        "model_identity_failures": 0,
        "reversal_agreements": 1,
        "reversal_pairs": 1,
    }
    serialized = json.dumps(summary)
    for forbidden in ("original", "ablated", "scores", "winner", "8.0", "6.0"):
        assert forbidden not in serialized
