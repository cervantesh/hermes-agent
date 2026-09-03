from __future__ import annotations

import json
import os

from hermes_cli import kanban_db as kb

from ..common.harness import OpaqueCorpus
from ..common.model_runtime import Cohort
from .runners import run_b_boundary_gate, run_context_case, run_isolation_probe
from .runtime import RepetitionModelResult


COHORT = Cohort("test", "test", "test", "test")


def _result(*, response: str, tools: dict[str, int]) -> RepetitionModelResult:
    return RepetitionModelResult(
        final_response=response,
        input_tokens=10,
        output_tokens=2,
        cache_read_tokens=20,
        cache_write_tokens=5,
        prompt_tokens=35,
        latency_ms=1.0,
        api_calls=1,
        tool_counts=tools,
        turn_exit_reason="completed",
    )


def test_d_arm_has_no_task_identity_or_tool_surface() -> None:
    corpus = OpaqueCorpus.generate(seed=377, record_count=4, value_bytes=8)
    expected = json.dumps(
        {"selected": {corpus.keys[1]: corpus.records[corpus.keys[1]]}},
        separators=(",", ":"),
    )

    def fake_model(**kwargs):
        assert os.environ.get("HERMES_KANBAN_TASK") is None
        assert kwargs["enabled_toolsets"] == ()
        return _result(response=expected, tools={})

    rows = run_context_case(
        cohort=COHORT,
        seed=377,
        record_count=4,
        value_bytes=8,
        requested_indexes=(1,),
        arms=("D",),
        model_call=fake_model,
    )

    assert rows[0]["external_oracle"] is True
    assert rows[0]["valid_observation"] is True
    assert rows[0]["outcome_source"] == "final_response"


def test_b_arm_scores_the_durable_worker_result() -> None:
    corpus = OpaqueCorpus.generate(seed=377, record_count=4, value_bytes=8)
    expected = json.dumps(
        {"selected": {corpus.keys[1]: corpus.records[corpus.keys[1]]}},
        separators=(",", ":"),
    )

    def fake_model(**kwargs):
        task_id = os.environ["HERMES_KANBAN_TASK"]
        with kb.connect_closing() as conn:
            assert kb.complete_task(conn, task_id, result=expected)
        return _result(
            response="worker completed",
            tools={"kanban_show": 1, "kanban_complete": 1},
        )

    rows = run_context_case(
        cohort=COHORT,
        seed=377,
        record_count=4,
        value_bytes=8,
        requested_indexes=(1,),
        arms=("B",),
        model_call=fake_model,
    )

    assert rows[0]["external_oracle"] is True
    assert rows[0]["valid_observation"] is True
    assert rows[0]["outcome_source"] == "task.result"
    assert rows[0]["task_status"] == "done"


def test_isolation_probe_scores_durable_result_and_hides_canary() -> None:
    def fake_model(**kwargs):
        requester = os.environ["HERMES_KANBAN_TASK"]
        owner = kwargs["user_message"].split("task_id ", 1)[1].split(".", 1)[0]
        with kb.connect_closing() as conn:
            source = kb.get_task(conn, owner).body
            assert kb.complete_task(
                conn, requester, result=json.dumps({"value": source})
            )
        assert source not in kwargs["user_message"]
        return _result(
            response="worker completed",
            tools={"kanban_show": 1, "kanban_complete": 1},
        )

    row = run_isolation_probe(
        cohort=COHORT,
        seed=91,
        relationship="declared_completed_parent",
        model_call=fake_model,
    )

    assert row["external_oracle"] is True
    assert row["valid_observation"] is True
    assert row["canary_disclosed_in_prompt"] is False


def test_invalid_b_boundary_does_not_open_confirmation() -> None:
    def invalid_model(**kwargs):
        return _result(response="{}", tools={})

    result = run_b_boundary_gate(cohort=COHORT, seed=377, model_call=invalid_model)

    assert result["expanded"] is False
    assert result["confirmation_allowed"] is False
    assert result["disposition"] == "INCONCLUSIVE"
    assert len(result["rows"]) == 1
