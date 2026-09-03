"""Direct provider transports with exact identity, budgets, and sanitized receipts."""

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


class ProviderContentError(ValueError):
    """The provider completed and billed a response without usable text."""


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


def _provider_transport_error(error: Exception) -> bool:
    """Recognize SDK transport failures without importing either provider SDK."""
    transport_names = {
        "APIConnectionError",
        "APITimeoutError",
        "ConnectError",
        "ConnectTimeout",
        "ReadError",
        "ReadTimeout",
        "WriteError",
        "WriteTimeout",
    }
    return any(cls.__name__ in transport_names for cls in type(error).__mro__)


def _retryable(error: Exception) -> bool:
    status = _status_code(error)
    return (
        status == 429
        or (status is not None and 500 <= status <= 599)
        or isinstance(error, (TimeoutError, ConnectionError))
        or _provider_transport_error(error)
    )


def _unknown_transport_receipt(
    *,
    agent: str,
    model: str,
    request: dict[str, Any],
    system_prompt: str,
    messages: list[dict[str, str]],
    attempts: int,
    started: float,
    error: Exception,
) -> dict[str, Any]:
    """Describe an indeterminate transport attempt without retaining private data."""
    return {
        "agent": agent,
        "requested_model": model,
        "returned_model": None,
        "request_sha256": _canonical_hash(request),
        "system_prompt_sha256": _text_hash(system_prompt),
        "messages_sha256": _canonical_hash(messages),
        "content_types": [],
        "finish_reason": None,
        "attempts": attempts,
        "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        "failure_type": type(error).__name__,
        "usage_unknown": True,
    }


def _response_text(response: Any) -> str:
    parts = []
    for block in response.content:
        block_type = getattr(block, "type", None)
        if block_type == "text":
            parts.append(str(block.text))
    if not parts:
        raise ProviderContentError("provider response contained no text block")
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
        before_attempt: Callable[[], None] | None = None,
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
        self.before_attempt = before_attempt
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
        usage_unknown = False
        for attempt in range(self.max_attempts):
            attempts = attempt + 1
            if self.before_attempt is not None:
                self.before_attempt()
            self.budget.begin_attempt()
            try:
                response = self.client.messages.create(**request)
                break
            except Exception as error:
                if _provider_transport_error(error):
                    usage_unknown = True
                    self.receipts.append(
                        _unknown_transport_receipt(
                            agent=agent,
                            model=self.model,
                            request=request,
                            system_prompt=system_prompt,
                            messages=messages,
                            attempts=attempts,
                            started=started,
                            error=error,
                        )
                    )
                if not _retryable(error) or attempts == self.max_attempts:
                    raise
                self.sleep(self.retry_waits[attempt])
        if response is None:
            raise RuntimeError("provider did not return a response")

        input_tokens = int(response.usage.input_tokens)
        output_tokens = int(response.usage.output_tokens)
        budget_error = None
        try:
            self.budget.commit_usage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                input_usd_per_million=self.input_usd_per_million,
                output_usd_per_million=self.output_usd_per_million,
            )
        except BudgetExceeded as error:
            budget_error = error
        content_types = [
            str(getattr(block, "type", "unknown")) for block in response.content
        ]
        if budget_error is not None:
            response_sha256 = _canonical_hash({
                "content_types": content_types,
                "stop_reason": str(response.stop_reason),
            })
            content_error = True
        else:
            try:
                text = _response_text(response)
            except ProviderContentError:
                response_sha256 = _canonical_hash({
                    "content_types": content_types,
                    "stop_reason": str(response.stop_reason),
                })
                content_error = True
            else:
                response_sha256 = _text_hash(text)
                content_error = False
        receipt = {
            "agent": agent,
            "requested_model": self.model,
            "returned_model": str(response.model),
            "request_sha256": _canonical_hash(request),
            "system_prompt_sha256": _text_hash(system_prompt),
            "messages_sha256": _canonical_hash(messages),
            "response_sha256": response_sha256,
            "content_types": content_types,
            "finish_reason": str(response.stop_reason),
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            },
            "attempts": attempts,
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "usage_unknown": usage_unknown,
        }
        self.receipts.append(receipt)
        if budget_error is not None:
            raise budget_error
        if response.model != self.model:
            raise ModelIdentityError(
                f"provider returned {response.model!r}, expected {self.model!r}"
            )
        if content_error:
            raise ProviderContentError("provider response contained no text block")
        return Generation(
            text=text,
            finish_reason=str(response.stop_reason),
            usage={"input_tokens": input_tokens, "output_tokens": output_tokens},
        )


class OpenAIChatBackend:
    """Pinned Chat Completions transport for the paper-family calibration judge."""

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
        before_attempt: Callable[[], None] | None = None,
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
        self.before_attempt = before_attempt
        self.receipts: list[dict[str, Any]] = []

    def complete(
        self,
        *,
        agent: str,
        system_prompt: str,
        messages: list[dict[str, str]],
        parameters: dict[str, Any],
    ) -> Generation:
        provider_messages = [
            {"role": "system", "content": system_prompt},
            *messages,
        ]
        request = {
            "model": self.model,
            "messages": provider_messages,
            "temperature": parameters["temperature"],
            "top_p": parameters["top_p"],
            "max_tokens": parameters["max_tokens"],
        }
        self.budget.begin_call(self.reserve_usd)
        started = time.perf_counter()
        response = None
        attempts = 0
        usage_unknown = False
        for attempt in range(self.max_attempts):
            attempts = attempt + 1
            if self.before_attempt is not None:
                self.before_attempt()
            self.budget.begin_attempt()
            try:
                response = self.client.chat.completions.create(**request)
                break
            except Exception as error:
                if _provider_transport_error(error):
                    usage_unknown = True
                    self.receipts.append(
                        _unknown_transport_receipt(
                            agent=agent,
                            model=self.model,
                            request=request,
                            system_prompt=system_prompt,
                            messages=messages,
                            attempts=attempts,
                            started=started,
                            error=error,
                        )
                    )
                if not _retryable(error) or attempts == self.max_attempts:
                    raise
                self.sleep(self.retry_waits[attempt])
        if response is None:
            raise RuntimeError("provider did not return a response")

        choice = response.choices[0]
        text = choice.message.content
        input_tokens = int(response.usage.prompt_tokens)
        output_tokens = int(response.usage.completion_tokens)
        budget_error = None
        try:
            self.budget.commit_usage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                input_usd_per_million=self.input_usd_per_million,
                output_usd_per_million=self.output_usd_per_million,
            )
        except BudgetExceeded as error:
            budget_error = error
        content_types = []
        if isinstance(text, str) and text:
            content_types.append("text")
            response_sha256 = _text_hash(text)
        else:
            if getattr(choice.message, "refusal", None):
                content_types.append("refusal")
            response_sha256 = _canonical_hash({
                "content_types": content_types,
                "finish_reason": str(choice.finish_reason),
            })
        receipt = {
            "agent": agent,
            "requested_model": self.model,
            "returned_model": str(response.model),
            "request_sha256": _canonical_hash(request),
            "system_prompt_sha256": _text_hash(system_prompt),
            "messages_sha256": _canonical_hash(messages),
            "response_sha256": response_sha256,
            "content_types": content_types,
            "finish_reason": str(choice.finish_reason),
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            },
            "attempts": attempts,
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "usage_unknown": usage_unknown,
        }
        self.receipts.append(receipt)
        if budget_error is not None:
            raise budget_error
        if response.model != self.model:
            raise ModelIdentityError(
                f"provider returned {response.model!r}, expected {self.model!r}"
            )
        if not isinstance(text, str) or not text:
            raise ProviderContentError("provider response contained no text")
        return Generation(
            text=text,
            finish_reason=str(choice.finish_reason),
            usage={"input_tokens": input_tokens, "output_tokens": output_tokens},
        )
