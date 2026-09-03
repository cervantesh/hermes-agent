from __future__ import annotations

import json

from ..common.model_runtime import Cohort, ModelResult
from .runner import run_relationship_probe


def test_real_agent_prompt_does_not_disclose_canary() -> None:
    captured = {}

    def fake_model(**kwargs) -> ModelResult:
        captured.update(kwargs)
        task_id = kwargs["user_message"].split("task_id ", 1)[1].split(".", 1)[0]
        from tools.kanban_tools import _handle_show

        document = json.loads(_handle_show({"task_id": task_id}))
        value = document["task"]["body"]
        return ModelResult(
            final_response=json.dumps({"value": value}, separators=(",", ":")),
            input_tokens=50,
            output_tokens=10,
            cache_read_tokens=0,
            latency_ms=20,
            api_calls=1,
            tool_counts={"kanban_show": 1},
        )

    result = run_relationship_probe(
        cohort=Cohort("test", "openai-codex", "gpt-5.4", "codex_responses"),
        seed=91,
        relationship="unrelated_same_board",
        model_call=fake_model,
    )

    assert result["external_oracle"] is True
    assert result["security_label"] == "POLICY_UNADJUDICATED"
    assert result["is_vulnerability"] is False
    assert result["canary_disclosed_in_prompt"] is False
    assert captured["enabled_toolsets"] == ("kanban",)
