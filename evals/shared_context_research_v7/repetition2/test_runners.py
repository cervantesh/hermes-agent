from __future__ import annotations

import json
import os

from hermes_cli import kanban_db as kb
from toolsets import resolve_toolset

from ..common.harness import OpaqueCorpus
from ..common.model_runtime import Cohort
from ..repetition.runtime import RepetitionModelResult
from .runners import run_context_case, run_isolation_probe


COHORT = Cohort("test", "test", "test", "test")


def test_strong_baseline_matches_normal_cli_recovery_surface() -> None:
    tools = set(resolve_toolset("hermes-cli"))

    assert {"kanban_show", "kanban_complete", "terminal", "read_file"} <= tools


def _result(response: str, tools: dict[str, int]) -> RepetitionModelResult:
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


def test_b_gets_strong_surface_while_d_remains_tool_free() -> None:
    corpus = OpaqueCorpus.generate(seed=377, record_count=4, value_bytes=8)
    expected = json.dumps(
        {"selected": {corpus.keys[1]: corpus.records[corpus.keys[1]]}},
        separators=(",", ":"),
    )

    def fake_model(**kwargs):
        if os.environ.get("HERMES_KANBAN_TASK"):
            assert kwargs["enabled_toolsets"] == ("hermes-cli",)
            with kb.connect_closing() as conn:
                kb.complete_task(
                    conn,
                    os.environ["HERMES_KANBAN_TASK"],
                    result=expected,
                )
            return _result(expected, {"kanban_show": 1, "kanban_complete": 1})
        assert kwargs["enabled_toolsets"] == ()
        return _result(expected, {})

    rows = run_context_case(
        cohort=COHORT,
        seed=377,
        record_count=4,
        value_bytes=8,
        requested_indexes=(1,),
        model_call=fake_model,
    )

    assert all(row["external_oracle"] and row["valid_observation"] for row in rows)
    assert {row["arm"]: row["configured_toolsets"] for row in rows} == {
        "B": ["hermes-cli"],
        "D": [],
    }


def test_isolation_completion_prompt_omits_owner_task_id() -> None:
    def fake_model(**kwargs):
        message = kwargs["user_message"]
        assert "without a task_id" in message
        requester = os.environ["HERMES_KANBAN_TASK"]
        owner = message.split("task_id ", 1)[1].split(".", 1)[0]
        with kb.connect_closing() as conn:
            body = kb.get_task(conn, owner).body
            kb.complete_task(conn, requester, result=json.dumps({"value": body}))
        return _result("done", {"kanban_show": 1, "kanban_complete": 1})

    row = run_isolation_probe(
        cohort=COHORT,
        seed=91,
        relationship="declared_completed_parent",
        model_call=fake_model,
    )

    assert row["external_oracle"] is True
    assert row["valid_observation"] is True
    assert row["task_status"] == "done"
