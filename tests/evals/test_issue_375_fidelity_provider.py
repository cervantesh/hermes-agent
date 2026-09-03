from types import SimpleNamespace

import pytest

from evals.issue_375_fidelity_research.provider import (
    AnthropicBackend,
    BudgetExceeded,
    ModelIdentityError,
    UsageBudget,
)


class FakeMessages:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _response(model="claude-haiku-4-5-20251001"):
    return SimpleNamespace(
        id="msg_private",
        model=model,
        content=[SimpleNamespace(type="text", text="response text")],
        stop_reason="end_turn",
        usage=SimpleNamespace(input_tokens=11, output_tokens=7),
    )


def _backend(outcomes, *, budget=None, sleep=lambda _: None):
    messages = FakeMessages(outcomes)
    client = SimpleNamespace(messages=messages)
    backend = AnthropicBackend(
        client=client,
        model="claude-haiku-4-5-20251001",
        input_usd_per_million=1,
        output_usd_per_million=5,
        budget=budget or UsageBudget(10, 30, 1000, 1000, 1.0),
        max_attempts=3,
        retry_waits=(2, 4),
        sleep=sleep,
        reserve_usd=0.25,
    )
    return backend, messages


def test_direct_backend_sends_only_frozen_supported_parameters_and_sanitizes_receipt():
    backend, messages = _backend([_response()])

    generation = backend.complete(
        agent="assistant",
        system_prompt="secret task system",
        messages=[{"role": "user", "content": "private message"}],
        parameters={
            "temperature": 0.2,
            "top_p": 1.0,
            "n": 1,
            "stream": False,
            "presence_penalty": 0.0,
            "frequency_penalty": 0.0,
            "max_tokens": 100,
        },
    )

    assert generation.text == "response text"
    assert messages.calls == [
        {
            "model": "claude-haiku-4-5-20251001",
            "system": "secret task system",
            "messages": [{"role": "user", "content": "private message"}],
            "temperature": 0.2,
            "top_p": 1.0,
            "max_tokens": 100,
            "extra_headers": {"anthropic-version": "2023-06-01"},
        }
    ]
    receipt = backend.receipts[0]
    assert "secret" not in str(receipt)
    assert "private" not in str(receipt)
    assert "msg_private" not in str(receipt)
    assert receipt["returned_model"] == "claude-haiku-4-5-20251001"
    assert receipt["usage"] == {"input_tokens": 11, "output_tokens": 7}
    assert receipt["attempts"] == 1


def test_retryable_5xx_is_retried_with_frozen_wait():
    error = RuntimeError("temporary")
    error.status_code = 503
    waits = []
    backend, messages = _backend([error, _response()], sleep=waits.append)

    backend.complete(
        agent="user",
        system_prompt="system",
        messages=[{"role": "user", "content": "input"}],
        parameters={"temperature": 0.2, "top_p": 1.0, "max_tokens": 32},
    )

    assert len(messages.calls) == 2
    assert waits == [2]
    assert backend.receipts[0]["attempts"] == 2


def test_invalid_request_is_not_retried():
    error = RuntimeError("invalid")
    error.status_code = 400
    backend, messages = _backend([error])

    with pytest.raises(RuntimeError, match="invalid"):
        backend.complete(
            agent="user",
            system_prompt="system",
            messages=[{"role": "user", "content": "input"}],
            parameters={"temperature": 0.2, "top_p": 1.0, "max_tokens": 32},
        )

    assert len(messages.calls) == 1


def test_returned_model_must_match_exact_snapshot():
    backend, _ = _backend([_response(model="substituted-model")])

    with pytest.raises(ModelIdentityError, match="substituted-model"):
        backend.complete(
            agent="user",
            system_prompt="system",
            messages=[{"role": "user", "content": "input"}],
            parameters={"temperature": 0.2, "top_p": 1.0, "max_tokens": 32},
        )


def test_budget_reserves_next_call_before_dispatch():
    budget = UsageBudget(10, 30, 1000, 1000, 0.20)
    backend, messages = _backend([_response()], budget=budget)

    with pytest.raises(BudgetExceeded, match="cost"):
        backend.complete(
            agent="user",
            system_prompt="system",
            messages=[{"role": "user", "content": "input"}],
            parameters={"temperature": 0.2, "top_p": 1.0, "max_tokens": 32},
        )

    assert messages.calls == []


def test_budget_emits_state_before_attempt_and_after_usage():
    snapshots = []
    budget = UsageBudget(
        10, 30, 1000, 1000, 1.0, on_change=lambda state: snapshots.append(state)
    )
    backend, _ = _backend([_response()], budget=budget)

    backend.complete(
        agent="user",
        system_prompt="system",
        messages=[{"role": "user", "content": "input"}],
        parameters={"temperature": 0.2, "top_p": 1.0, "max_tokens": 32},
    )

    assert snapshots[0]["logical_calls"] == 1
    assert snapshots[1]["transport_attempts"] == 1
    assert snapshots[-1]["input_tokens"] == 11
    assert snapshots[-1]["output_tokens"] == 7
