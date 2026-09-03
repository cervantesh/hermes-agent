"""Measured Hermes model runtime for the corrected V7 repetition."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import time
from typing import Any, Callable

from ..common.model_runtime import Cohort, _tool_counts


@dataclass(frozen=True)
class RepetitionModelResult:
    final_response: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    prompt_tokens: int
    latency_ms: float
    api_calls: int
    tool_counts: Mapping[str, int]
    turn_exit_reason: str


def _measured_int(raw: Mapping[str, Any], name: str) -> int:
    value = raw.get(name)
    if not isinstance(value, (int, float)):
        raise RuntimeError(f"scored run has no measured {name} field")
    return int(value)


def run_model(
    *,
    cohort: Cohort,
    user_message: str,
    system_message: str,
    enabled_toolsets: Iterable[str],
    agent_factory: Callable[..., Any] | None = None,
) -> RepetitionModelResult:
    if agent_factory is None:
        from run_agent import AIAgent

        agent_factory = AIAgent
    agent = agent_factory(
        provider=cohort.provider,
        model=cohort.model,
        api_mode=cohort.api_mode,
        api_key=None,
        quiet_mode=True,
        skip_context_files=True,
        skip_memory=True,
        enabled_toolsets=list(enabled_toolsets),
        max_iterations=12,
        platform="cli",
    )
    started = time.perf_counter()
    try:
        raw = agent.run_conversation(
            user_message=user_message,
            system_message=system_message,
        )
    finally:
        elapsed_ms = (time.perf_counter() - started) * 1000
        agent.close()

    input_tokens = _measured_int(raw, "input_tokens")
    cache_read_tokens = _measured_int(raw, "cache_read_tokens")
    cache_write_tokens = _measured_int(raw, "cache_write_tokens")
    prompt_tokens = _measured_int(raw, "prompt_tokens")
    if prompt_tokens != input_tokens + cache_read_tokens + cache_write_tokens:
        raise RuntimeError("Hermes canonical prompt-token invariant failed")
    return RepetitionModelResult(
        final_response=str(raw.get("final_response") or ""),
        input_tokens=input_tokens,
        output_tokens=_measured_int(raw, "output_tokens"),
        cache_read_tokens=cache_read_tokens,
        cache_write_tokens=cache_write_tokens,
        prompt_tokens=prompt_tokens,
        latency_ms=elapsed_ms,
        api_calls=int(raw.get("api_calls") or 0),
        tool_counts=_tool_counts(raw),
        turn_exit_reason=str(raw.get("turn_exit_reason") or ""),
    )
