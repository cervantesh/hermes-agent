from __future__ import annotations

import json

import pytest

from .model_runtime import Cohort, exact_json_result, run_model


class _FakeAgent:
    def __init__(self, response: dict, **kwargs) -> None:
        self.response = response
        self.kwargs = kwargs
        self.closed = False

    def run_conversation(self, user_message: str, system_message: str) -> dict:
        assert user_message
        assert system_message
        return self.response

    def close(self) -> None:
        self.closed = True


def test_model_runtime_records_provider_usage_without_estimating() -> None:
    response = {
        "final_response": '{"selected":{"key-1":"value-1"}}',
        "input_tokens": 120,
        "output_tokens": 15,
        "cache_read_tokens": 30,
        "api_calls": 1,
        "messages": [
            {
                "role": "assistant",
                "tool_calls": [{"function": {"name": "kanban_show"}}],
            }
        ],
    }
    created = []

    def factory(**kwargs):
        agent = _FakeAgent(response, **kwargs)
        created.append(agent)
        return agent

    result = run_model(
        cohort=Cohort(
            id="openai-control",
            provider="openai-codex",
            model="gpt-5.4",
            api_mode="codex_responses",
        ),
        user_message="select key-1",
        system_message="return JSON",
        enabled_toolsets=(),
        agent_factory=factory,
    )

    assert result.input_tokens == 120
    assert result.output_tokens == 15
    assert result.cache_read_tokens == 30
    assert result.token_source == "hermes_run_result"
    assert result.tool_counts == {"kanban_show": 1}
    assert created[0].closed
    assert created[0].kwargs["provider"] == "openai-codex"


def test_model_runtime_rejects_missing_usage_for_scored_run() -> None:
    def factory(**kwargs):
        return _FakeAgent({"final_response": "{}"}, **kwargs)

    with pytest.raises(RuntimeError, match="usage fields"):
        run_model(
            cohort=Cohort("c", "anthropic", "claude-sonnet-4-6", "anthropic_messages"),
            user_message="work",
            system_message="system",
            enabled_toolsets=(),
            agent_factory=factory,
        )


def test_external_json_oracle_is_strict() -> None:
    expected = {"selected": {"key-1": "value-1"}}
    assert exact_json_result(json.dumps(expected), expected)
    assert not exact_json_result("```json\n" + json.dumps(expected) + "\n```", expected)
    assert not exact_json_result('{"selected":{"key-1":"wrong"}}', expected)
