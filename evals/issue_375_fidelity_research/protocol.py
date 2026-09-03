"""Paper-era CAMEL AI Society role-play lifecycle reconstruction."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

import tiktoken


DEFAULT_PARAMETERS = {
    "temperature": 0.2,
    "top_p": 1.0,
    "n": 1,
    "stream": False,
    "presence_penalty": 0.0,
    "frequency_penalty": 0.0,
}
REPEAT_WORDS = (
    "goodbye",
    "good bye",
    "thank",
    "bye",
    "welcome",
    "language model",
)


@dataclass(frozen=True)
class Generation:
    text: str
    finish_reason: str
    usage: dict[str, int]
    terminated: bool = False


class CompletionBackend(Protocol):
    def complete(
        self,
        *,
        agent: str,
        system_prompt: str,
        messages: list[dict[str, str]],
        parameters: dict[str, Any],
    ) -> Generation: ...


@dataclass(frozen=True)
class RolePrompts:
    assistant: str
    user: str


@dataclass(frozen=True)
class RolePlayResult:
    transcript: list[dict[str, str]]
    termination_reason: str
    num_role_messages: int
    calls: int
    protocol_violations: tuple[str, ...] = field(default_factory=tuple)


class _AgentState:
    def __init__(
        self,
        name: str,
        system_prompt: str,
        backend: CompletionBackend,
        token_counter: Callable[[list[dict[str, str]]], int],
        token_limit: int,
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.backend = backend
        self.token_counter = token_counter
        self.token_limit = token_limit
        self.messages: list[dict[str, str]] = []
        self.calls = 0

    def step(self, content: str) -> Generation:
        self.messages.append({"role": "user", "content": content})
        provider_messages = [
            {"role": "system", "content": self.system_prompt},
            *self.messages,
        ]
        input_tokens = self.token_counter(provider_messages)
        if input_tokens >= self.token_limit:
            return Generation(
                text="",
                finish_reason="max_tokens_exceeded",
                usage={},
                terminated=True,
            )
        parameters = {
            **DEFAULT_PARAMETERS,
            "max_tokens": self.token_limit - input_tokens,
        }
        generation = self.backend.complete(
            agent=self.name,
            system_prompt=self.system_prompt,
            messages=self.messages,
            parameters=parameters,
        )
        self.calls += 1
        if not generation.terminated:
            self.messages.append({"role": "assistant", "content": generation.text})
        return generation


def initial_relay_message(user_system_prompt: str) -> str:
    return (
        f"{user_system_prompt}. Now start to give me introductions one by one. "
        "Only reply with Instruction and Input."
    )


def historical_gpt35_token_count(messages: list[dict[str, str]]) -> int:
    """Reproduce the pinned CAMEL GPT-3.5 ChatML accounting algorithm."""
    encoding = tiktoken.get_encoding("cl100k_base")
    count = 0
    for message in messages:
        count += 4
        for key, value in message.items():
            count += len(encoding.encode(value))
            if key == "name":
                count -= 1
    return count + 2


def run_role_play(
    prompts: RolePrompts,
    backend: CompletionBackend,
    *,
    max_role_messages: int = 40,
    token_counter: Callable[[list[dict[str, str]]], int] = historical_gpt35_token_count,
    token_limit: int = 4096,
) -> RolePlayResult:
    """Run the pinned historical state machine, including discarded priming."""
    if max_role_messages < 0 or max_role_messages % 2:
        raise ValueError("max_role_messages must be a non-negative even number")

    assistant = _AgentState(
        "assistant", prompts.assistant, backend, token_counter, token_limit
    )
    user = _AgentState("user", prompts.user, backend, token_counter, token_limit)

    priming = assistant.step(prompts.assistant)
    if priming.terminated:
        return RolePlayResult([], "assistant: max_tokens_exceeded", 0, assistant.calls)

    assistant_message = initial_relay_message(prompts.user)
    transcript: list[dict[str, str]] = []
    user_no_instruction = 0
    repeat_word_counter = 0
    termination_reason = "max_num_messages"

    while len(transcript) < max_role_messages:
        user_generation = user.step(assistant_message)
        if user_generation.terminated:
            termination_reason = f"user: {user_generation.finish_reason}"
            break
        user_message = user_generation.text

        assistant_generation = assistant.step(user_message)
        if assistant_generation.terminated:
            termination_reason = f"assistant: {assistant_generation.finish_reason}"
            break
        assistant_message = assistant_generation.text

        if "Instruction:" not in user_message:
            user_no_instruction += 1
            if user_no_instruction == 3:
                termination_reason = "user_no_instruct_threshold"
                break
        else:
            user_no_instruction = 0

        if "Instruction:" in assistant_message:
            termination_reason = "assistant_instruct_threshold"
            break

        repeated = False
        for word in REPEAT_WORDS:
            combined = f"{user_message}\n{assistant_message}".lower()
            if word in combined:
                repeat_word_counter += 1
                if repeat_word_counter == 4:
                    termination_reason = "repeat_word_threshold"
                    repeated = True
                    break
            else:
                repeat_word_counter = 0
        if repeated:
            break

        transcript.append({"role": "user", "content": user_message})
        if "<CAMEL_TASK_DONE>" in user_message:
            termination_reason = "<CAMEL_TASK_DONE>"
            break
        transcript.append({"role": "assistant", "content": assistant_message})

    return RolePlayResult(
        transcript=transcript,
        termination_reason=termination_reason,
        num_role_messages=len(transcript),
        calls=assistant.calls + user.calls,
    )
