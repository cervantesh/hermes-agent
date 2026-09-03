from __future__ import annotations

import pytest

from ..common.model_runtime import Cohort
from .runtime import run_model


class FakeAgent:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def run_conversation(self, **kwargs):
        return {
            "final_response": '{"ok":true}',
            "input_tokens": 10,
            "output_tokens": 2,
            "cache_read_tokens": 20,
            "cache_write_tokens": 5,
            "prompt_tokens": 35,
            "api_calls": 1,
            "turn_exit_reason": "completed",
            "messages": [],
        }

    def close(self):
        return None


def test_runtime_requires_and_preserves_canonical_prompt_tokens() -> None:
    result = run_model(
        cohort=Cohort("c", "p", "m", "a"),
        user_message="u",
        system_message="s",
        enabled_toolsets=(),
        agent_factory=FakeAgent,
    )

    assert result.prompt_tokens == 35
    assert result.prompt_tokens == (
        result.input_tokens + result.cache_read_tokens + result.cache_write_tokens
    )


def test_runtime_rejects_incoherent_provider_usage() -> None:
    class BadAgent(FakeAgent):
        def run_conversation(self, **kwargs):
            raw = super().run_conversation(**kwargs)
            raw["prompt_tokens"] = 34
            return raw

    with pytest.raises(RuntimeError, match="prompt-token invariant"):
        run_model(
            cohort=Cohort("c", "p", "m", "a"),
            user_message="u",
            system_message="s",
            enabled_toolsets=(),
            agent_factory=BadAgent,
        )
