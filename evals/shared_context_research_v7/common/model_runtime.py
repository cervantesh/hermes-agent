"""Real Hermes model invocation with explicit, non-estimated usage evidence."""

from __future__ import annotations

from dataclasses import dataclass
from collections import Counter
import json
import time
from typing import Any, Callable, Iterable, Mapping


@dataclass(frozen=True)
class Cohort:
    id: str
    provider: str
    model: str
    api_mode: str


@dataclass(frozen=True)
class ModelResult:
    final_response: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    latency_ms: float
    api_calls: int
    tool_counts: Mapping[str, int]
    token_source: str = "hermes_run_result"


def _usage(result: Mapping[str, Any]) -> dict[str, int]:
    nested = result.get("tokens") or result.get("token_usage") or {}
    usage = nested if isinstance(nested, Mapping) else {}

    def value(name: str) -> int | None:
        raw = result.get(name, usage.get(name))
        return int(raw) if isinstance(raw, (int, float)) else None

    input_tokens = value("input_tokens")
    output_tokens = value("output_tokens")
    cache_read_tokens = value("cache_read_tokens")
    if input_tokens is None or output_tokens is None:
        raise RuntimeError("scored run has no measured provider usage fields")
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_tokens": cache_read_tokens or 0,
    }


def _tool_counts(result: Mapping[str, Any]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    messages = result.get("messages")
    if not isinstance(messages, list):
        return {}
    for message in messages:
        if not isinstance(message, Mapping):
            continue
        calls = message.get("tool_calls")
        if not isinstance(calls, list):
            continue
        for call in calls:
            if not isinstance(call, Mapping):
                continue
            function = call.get("function")
            function = function if isinstance(function, Mapping) else {}
            name = function.get("name") or call.get("name")
            if isinstance(name, str) and name:
                counts[name] += 1
    return dict(sorted(counts.items()))


def run_model(
    *,
    cohort: Cohort,
    user_message: str,
    system_message: str,
    enabled_toolsets: Iterable[str],
    agent_factory: Callable[..., Any] | None = None,
) -> ModelResult:
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
    usage = _usage(raw)
    return ModelResult(
        final_response=str(raw.get("final_response") or ""),
        input_tokens=usage["input_tokens"],
        output_tokens=usage["output_tokens"],
        cache_read_tokens=usage["cache_read_tokens"],
        latency_ms=elapsed_ms,
        api_calls=int(raw.get("api_calls") or 0),
        tool_counts=_tool_counts(raw),
    )


def exact_json_result(text: str, expected: Mapping[str, Any]) -> bool:
    try:
        actual = json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return False
    return actual == expected
