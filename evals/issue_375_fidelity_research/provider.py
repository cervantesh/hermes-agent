"""Direct Anthropic transport with exact identity, budgets, and sanitized receipts."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Callable

from .protocol import Generation


class BudgetExceeded(RuntimeError):
    pass


class ModelIdentityError(RuntimeError):
    pass


@dataclass
class UsageBudget:
    max_logical_calls: int
    max_transport_attempts: int
    max_input_tokens: int
    max_output_tokens: int
    max_cost_usd: float
    on_change: Callable[[dict[str, Any]], None] | None = None
    logical_calls: int = 0
    transport_attempts: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0

    def snapshot(self) -> dict[str, Any]:
        return {
            "max_logical_calls": self.max_logical_calls,
            "max_transport_attempts": self.max_transport_attempts,
            "max_input_tokens": self.max_input_tokens,
            "max_output_tokens": self.max_output_tokens,
            "max_cost_usd": self.max_cost_usd,
            "logical_calls": self.logical_calls,
            "transport_attempts": self.transport_attempts,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": self.cost_usd,
        }

    def _changed(self) -> None:
        if self.on_change is not None:
            self.on_change(self.snapshot())

    def begin_call(self, reserve_usd: float) -> None:
        if self.logical_calls + 1 > self.max_logical_calls:
            raise BudgetExceeded("logical call cap would be exceeded")
        if self.cost_usd + reserve_usd > self.max_cost_usd:
            raise BudgetExceeded("cost cap would be exceeded by the next-call reserve")
        self.logical_calls += 1
        self._changed()

    def begin_attempt(self) -> None:
        if self.transport_attempts + 1 > self.max_transport_attempts:
            raise BudgetExceeded("transport attempt cap would be exceeded")
        self.transport_attempts += 1
        self._changed()

    def commit_usage(
        self,
        *,
        input_tokens: int,
        output_tokens: int,
        input_usd_per_million: float,
        output_usd_per_million: float,
    ) -> None:
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.cost_usd += (
            input_tokens * input_usd_per_million
            + output_tokens * output_usd_per_million
        ) / 1_000_000
        self._changed()
        if self.input_tokens > self.max_input_tokens:
            raise BudgetExceeded("input token cap was exceeded")
        if self.output_tokens > self.max_output_tokens:
            raise BudgetExceeded("output token cap was exceeded")
        if self.cost_usd > self.max_cost_usd:
            raise BudgetExceeded("cost cap was exceeded")


def _canonical_hash(value: Any) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _text_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _status_code(error: Exception) -> int | None:
    status = getattr(error, "status_code", None)
    return status if isinstance(status, int) else None


def _retryable(error: Exception) -> bool:
    status = _status_code(error)
    return (
        status == 429
        or (status is not None and 500 <= status <= 599)
        or isinstance(error, (TimeoutError, ConnectionError))
    )


def _response_text(response: Any) -> str:
    parts = []
    for block in response.content:
        block_type = getattr(block, "type", None)
        if block_type == "text":
            parts.append(str(block.text))
    if not parts:
        raise ValueError("provider response contained no text block")
    return "".join(parts)


class AnthropicBackend:
    def __init__(
        self,
        *,
        client: Any,
        model: str,
        input_usd_per_million: float,
        output_usd_per_million: float,
        budget: UsageBudget,
        max_attempts: int,
        retry_waits: tuple[float, ...],
        sleep: Callable[[float], None] = time.sleep,
        reserve_usd: float,
    ) -> None:
        if max_attempts != len(retry_waits) + 1:
            raise ValueError("retry_waits must provide one wait per retry")
        self.client = client
        self.model = model
        self.input_usd_per_million = input_usd_per_million
        self.output_usd_per_million = output_usd_per_million
        self.budget = budget
        self.max_attempts = max_attempts
        self.retry_waits = retry_waits
        self.sleep = sleep
        self.reserve_usd = reserve_usd
        self.receipts: list[dict[str, Any]] = []

    def complete(
        self,
        *,
        agent: str,
        system_prompt: str,
        messages: list[dict[str, str]],
        parameters: dict[str, Any],
    ) -> Generation:
        request = {
            "model": self.model,
            "system": system_prompt,
            "messages": messages,
            "temperature": parameters["temperature"],
            "max_tokens": parameters["max_tokens"],
            "extra_headers": {"anthropic-version": "2023-06-01"},
        }
        self.budget.begin_call(self.reserve_usd)
        started = time.perf_counter()
        response = None
        attempts = 0
        for attempt in range(self.max_attempts):
            attempts = attempt + 1
            self.budget.begin_attempt()
            try:
                response = self.client.messages.create(**request)
                break
            except Exception as error:
                if not _retryable(error) or attempts == self.max_attempts:
                    raise
                self.sleep(self.retry_waits[attempt])
        if response is None:
            raise RuntimeError("provider did not return a response")

        text = _response_text(response)
        input_tokens = int(response.usage.input_tokens)
        output_tokens = int(response.usage.output_tokens)
        self.budget.commit_usage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_usd_per_million=self.input_usd_per_million,
            output_usd_per_million=self.output_usd_per_million,
        )
        receipt = {
            "agent": agent,
            "requested_model": self.model,
            "returned_model": str(response.model),
            "request_sha256": _canonical_hash(request),
            "system_prompt_sha256": _text_hash(system_prompt),
            "messages_sha256": _canonical_hash(messages),
            "response_sha256": _text_hash(text),
            "finish_reason": str(response.stop_reason),
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            },
            "attempts": attempts,
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        }
        self.receipts.append(receipt)
        if response.model != self.model:
            raise ModelIdentityError(
                f"provider returned {response.model!r}, expected {self.model!r}"
            )
        return Generation(
            text=text,
            finish_reason=str(response.stop_reason),
            usage={"input_tokens": input_tokens, "output_tokens": output_tokens},
        )
