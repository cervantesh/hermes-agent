from types import SimpleNamespace

import pytest

from evals.issue_375_fidelity_research.provider import (
    AnthropicBackend,
    BudgetExceeded,
    ModelIdentityError,
    OpenAIChatBackend,
    ProviderContentError,
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


def _backend(outcomes, *, budget=None, sleep=lambda _: None, before_attempt=None):
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
        before_attempt=before_attempt,
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


def test_before_attempt_guard_is_rechecked_for_transport_retry():
    error = RuntimeError("temporary")
    error.status_code = 503
    expired = [False]

    def guard():
        if expired[0]:
            raise RuntimeError("deadline")

    backend, messages = _backend(
        [error, _response()],
        sleep=lambda _: expired.__setitem__(0, True),
        before_attempt=guard,
    )

    with pytest.raises(RuntimeError, match="deadline"):
        backend.complete(
            agent="user",
            system_prompt="system",
            messages=[{"role": "user", "content": "input"}],
            parameters={"temperature": 0.2, "top_p": 1.0, "max_tokens": 32},
        )

    assert len(messages.calls) == 1


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


def test_non_text_anthropic_response_accounts_usage_and_receipt_before_failure():
    response = SimpleNamespace(
        id="msg_private",
        model="claude-haiku-4-5-20251001",
        content=[SimpleNamespace(type="thinking", thinking="private chain")],
        stop_reason="end_turn",
        usage=SimpleNamespace(input_tokens=17, output_tokens=9),
    )
    budget = UsageBudget(10, 30, 1000, 1000, 1.0)
    backend, _ = _backend([response], budget=budget)

    with pytest.raises(ProviderContentError, match="no text block"):
        backend.complete(
            agent="assistant",
            system_prompt="system",
            messages=[{"role": "user", "content": "input"}],
            parameters={"temperature": 0.2, "top_p": 1.0, "max_tokens": 32},
        )

    assert budget.input_tokens == 17
    assert budget.output_tokens == 9
    assert backend.receipts[0]["content_types"] == ["thinking"]
    assert "private chain" not in str(backend.receipts[0])


def test_anthropic_threshold_crossing_still_records_sanitized_receipt():
    budget = UsageBudget(10, 30, 5, 1000, 1.0)
    backend, _ = _backend([_response()], budget=budget)

    with pytest.raises(BudgetExceeded, match="input token"):
        backend.complete(
            agent="assistant",
            system_prompt="private system",
            messages=[{"role": "user", "content": "private input"}],
            parameters={"temperature": 0.2, "top_p": 1.0, "max_tokens": 32},
        )

    assert budget.input_tokens == 11
    assert backend.receipts[0]["usage"] == {"input_tokens": 11, "output_tokens": 7}
    assert "private" not in str(backend.receipts[0])


def test_openai_backend_uses_exact_chat_snapshot_and_sanitizes_receipt():
    completions = FakeMessages([
        SimpleNamespace(
            model="gpt-4-0613",
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="8 6\nprivate rationale"),
                    finish_reason="stop",
                )
            ],
            usage=SimpleNamespace(prompt_tokens=13, completion_tokens=5),
        )
    ])
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    backend = OpenAIChatBackend(
        client=client,
        model="gpt-4-0613",
        input_usd_per_million=30,
        output_usd_per_million=60,
        budget=UsageBudget(10, 30, 1000, 1000, 2.0),
        max_attempts=3,
        retry_waits=(2, 4),
        sleep=lambda _: None,
        reserve_usd=0.5,
    )

    generation = backend.complete(
        agent="judge_fidelity_forward",
        system_prompt="private paper system",
        messages=[{"role": "user", "content": "private answers"}],
        parameters={"temperature": 0.0, "top_p": 1.0, "max_tokens": 100},
    )

    assert generation.text == "8 6\nprivate rationale"
    assert completions.calls == [
        {
            "model": "gpt-4-0613",
            "messages": [
                {"role": "system", "content": "private paper system"},
                {"role": "user", "content": "private answers"},
            ],
            "temperature": 0.0,
            "top_p": 1.0,
            "max_tokens": 100,
        }
    ]
    receipt = backend.receipts[0]
    assert receipt["returned_model"] == "gpt-4-0613"
    assert receipt["usage"] == {"input_tokens": 13, "output_tokens": 5}
    assert "private" not in str(receipt)


def test_non_text_openai_response_accounts_usage_and_refusal_metadata():
    completions = FakeMessages([
        SimpleNamespace(
            model="gpt-4-0613",
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=None, refusal="private refusal"),
                    finish_reason="stop",
                )
            ],
            usage=SimpleNamespace(prompt_tokens=19, completion_tokens=4),
        )
    ])
    budget = UsageBudget(10, 30, 1000, 1000, 2.0)
    backend = OpenAIChatBackend(
        client=SimpleNamespace(chat=SimpleNamespace(completions=completions)),
        model="gpt-4-0613",
        input_usd_per_million=30,
        output_usd_per_million=60,
        budget=budget,
        max_attempts=3,
        retry_waits=(2, 4),
        sleep=lambda _: None,
        reserve_usd=0.5,
    )

    with pytest.raises(ProviderContentError, match="no text"):
        backend.complete(
            agent="judge_fidelity_forward",
            system_prompt="system",
            messages=[{"role": "user", "content": "answers"}],
            parameters={"temperature": 0.0, "top_p": 1.0, "max_tokens": 100},
        )

    assert budget.input_tokens == 19
    assert budget.output_tokens == 4
    assert backend.receipts[0]["content_types"] == ["refusal"]
    assert "private refusal" not in str(backend.receipts[0])


def test_openai_threshold_crossing_still_records_sanitized_receipt():
    completions = FakeMessages([
        SimpleNamespace(
            model="gpt-4-0613",
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="8 6\nprivate rationale"),
                    finish_reason="stop",
                )
            ],
            usage=SimpleNamespace(prompt_tokens=13, completion_tokens=5),
        )
    ])
    budget = UsageBudget(10, 30, 5, 1000, 2.0)
    backend = OpenAIChatBackend(
        client=SimpleNamespace(chat=SimpleNamespace(completions=completions)),
        model="gpt-4-0613",
        input_usd_per_million=30,
        output_usd_per_million=60,
        budget=budget,
        max_attempts=3,
        retry_waits=(2, 4),
        sleep=lambda _: None,
        reserve_usd=0.5,
    )

    with pytest.raises(BudgetExceeded, match="input token"):
        backend.complete(
            agent="judge_fidelity_forward",
            system_prompt="private system",
            messages=[{"role": "user", "content": "private answers"}],
            parameters={"temperature": 0.0, "top_p": 1.0, "max_tokens": 100},
        )

    assert budget.input_tokens == 13
    assert backend.receipts[0]["usage"] == {"input_tokens": 13, "output_tokens": 5}
    assert "private" not in str(backend.receipts[0])
