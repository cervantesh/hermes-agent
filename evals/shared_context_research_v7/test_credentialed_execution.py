from __future__ import annotations

from .common.model_runtime import Cohort, ModelResult
from . import credentialed_execution as execution


def _result() -> ModelResult:
    return ModelResult(
        final_response='{"ok":true}',
        input_tokens=1,
        output_tokens=1,
        cache_read_tokens=0,
        latency_ms=1.0,
        api_calls=1,
        tool_counts={},
    )


def test_non_codex_cohort_does_not_read_or_persist_codex_tokens(monkeypatch) -> None:
    monkeypatch.setattr(
        execution,
        "_load_codex_cli_tokens",
        lambda: (_ for _ in ()).throw(AssertionError("must not read Codex auth")),
    )
    monkeypatch.setattr(execution, "run_model", lambda **kwargs: _result())

    result = execution.run_authorized_model(
        cohort=Cohort("anthropic", "anthropic", "claude", "anthropic_messages"),
        user_message="u",
        system_message="s",
        enabled_toolsets=(),
    )

    assert result.api_calls == 1


def test_codex_cohort_persists_only_nonrefreshable_temp_pair(monkeypatch) -> None:
    saved: list[dict[str, str]] = []
    monkeypatch.setattr(
        execution,
        "_load_codex_cli_tokens",
        lambda: {"access_token": "access", "refresh_token": "real-refresh"},
    )
    monkeypatch.setattr(execution, "_codex_token_is_expiring", lambda *_: False)
    monkeypatch.setattr(execution, "_save_temp_codex_tokens", saved.append)
    monkeypatch.setattr(execution, "run_model", lambda **kwargs: _result())

    execution.run_authorized_model(
        cohort=Cohort("codex", "openai-codex", "gpt", "codex_responses"),
        user_message="u",
        system_message="s",
        enabled_toolsets=(),
    )

    assert saved == [
        {
            "access_token": "access",
            "refresh_token": execution.NON_REFRESHABLE_SENTINEL,
        }
    ]


def test_codex_cohort_aborts_before_persist_when_token_is_near_expiry(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        execution,
        "_load_codex_cli_tokens",
        lambda: {"access_token": "access", "refresh_token": "real-refresh"},
    )
    monkeypatch.setattr(execution, "_codex_token_is_expiring", lambda *_: True)
    monkeypatch.setattr(
        execution,
        "_save_temp_codex_tokens",
        lambda *_: (_ for _ in ()).throw(AssertionError("must not persist")),
    )

    try:
        execution.run_authorized_model(
            cohort=Cohort("codex", "openai-codex", "gpt", "codex_responses"),
            user_message="u",
            system_message="s",
            enabled_toolsets=(),
        )
    except RuntimeError as exc:
        assert "30 minutes" in str(exc)
    else:
        raise AssertionError("near-expiry token must abort")
