"""Protocol-faithful CAMEL RolePlaying orchestration for product research.

The production Hermes tree is not modified. Prompt templates are loaded at
runtime from an independently cloned, pinned Apache-2.0 CAMEL checkout.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import subprocess
from typing import Callable, Literal


PAPER_CAMEL_COMMIT = "c402032a7f7cd27e196356fbcf413c521a8cb4ca"
TASK_DONE = "<CAMEL_TASK_DONE>"
PAPER_MESSAGE_LIMIT = 40

_PROMPT_PATHS = {
    "specifier": "prompts/ai_society/task_specify_prompt.txt",
    "assistant": "prompts/ai_society/assistant_prompt_with_task.txt",
    "user": "prompts/ai_society/user_prompt_with_task.txt",
}


@dataclass(frozen=True)
class PromptBundle:
    specifier: str
    assistant: str
    user: str
    source_commit: str
    hashes: dict[str, str]


@dataclass(frozen=True)
class TurnResult:
    text: str
    history: list[dict]
    api_calls: int = 1
    tokens: dict = field(default_factory=dict)
    tool_trace: list[dict] = field(default_factory=list)


@dataclass(frozen=True)
class ProtocolMessage:
    sequence: int
    speaker: Literal["ai_user", "ai_assistant"]
    content: str


@dataclass
class CamelRun:
    original_task: str
    specified_task: str
    assistant_role: str
    user_role: str
    messages: list[ProtocolMessage]
    termination: str
    final_assistant_text: str
    prompt_hashes: dict[str, str]
    api_calls: int
    tool_trace: list[dict] = field(default_factory=list)
    tokens: dict[str, int] = field(default_factory=dict)


TurnCallable = Callable[[str, str, str, list[dict]], TurnResult]


def _git_show(repo: Path, revision: str, path: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), "show", f"{revision}:{path}"],
        text=True,
        encoding="utf-8",
    )


def load_paper_prompts(camel_repo: Path) -> PromptBundle:
    """Load and content-pin the paper-era prompt templates."""
    camel_repo = camel_repo.resolve()
    subprocess.check_call(
        ["git", "-C", str(camel_repo), "cat-file", "-e", PAPER_CAMEL_COMMIT]
    )
    content = {
        name: _git_show(camel_repo, PAPER_CAMEL_COMMIT, path)
        for name, path in _PROMPT_PATHS.items()
    }
    hashes = {
        name: hashlib.sha256(text.encode("utf-8")).hexdigest()
        for name, text in content.items()
    }
    return PromptBundle(
        specifier=content["specifier"],
        assistant=content["assistant"],
        user=content["user"],
        source_commit=PAPER_CAMEL_COMMIT,
        hashes=hashes,
    )


def render_specifier_prompt(
    template: str,
    *,
    task: str,
    assistant_role: str,
    user_role: str,
) -> str:
    return (
        template.replace("<ASSISTANT_ROLE>", assistant_role)
        .replace("<USER_ROLE>", user_role)
        .replace("<TASK>", task)
        .replace("<WORD_LIMIT>", "50")
    )


def render_role_prompts(
    bundle: PromptBundle,
    *,
    task: str,
    assistant_role: str,
    user_role: str,
) -> tuple[str, str]:
    replacements = {
        "<ASSISTANT_ROLE>": assistant_role,
        "<USER_ROLE>": user_role,
        "<TASK>": task,
    }

    def render(template: str) -> str:
        for key, value in replacements.items():
            template = template.replace(key, value)
        return template

    return render(bundle.assistant), render(bundle.user)


def is_exact_done(text: str) -> bool:
    return text.strip() == TASK_DONE


def assert_conformant(run: CamelRun) -> None:
    """Raise when the recorded run violates the frozen protocol contract."""
    if not run.specified_task.strip():
        raise AssertionError("task specifier returned an empty task")
    if len(run.messages) > PAPER_MESSAGE_LIMIT:
        raise AssertionError("paper message limit exceeded")
    for index, message in enumerate(run.messages, start=1):
        expected = "ai_user" if index % 2 else "ai_assistant"
        if message.sequence != index or message.speaker != expected:
            raise AssertionError("role alternation violated")
    done_messages = [m for m in run.messages if is_exact_done(m.content)]
    if done_messages and any(m.speaker != "ai_user" for m in done_messages):
        raise AssertionError("only the AI User may terminate")
    if run.termination == "task_done":
        if not run.messages or not is_exact_done(run.messages[-1].content):
            raise AssertionError("task_done termination lacks exact terminal token")
    elif run.termination == "message_limit":
        if len(run.messages) != PAPER_MESSAGE_LIMIT:
            raise AssertionError("message-limit termination occurred early")
    else:
        raise AssertionError(f"unknown termination: {run.termination}")


def run_role_playing(
    *,
    original_task: str,
    assistant_role: str,
    user_role: str,
    bundle: PromptBundle,
    turn: TurnCallable,
) -> CamelRun:
    """Execute task specification and the paper's two-role alternating loop."""
    specifier_input = render_specifier_prompt(
        bundle.specifier,
        task=original_task,
        assistant_role=assistant_role,
        user_role=user_role,
    )
    specifier = turn(
        "task_specifier",
        "You can make a task more specific. Return only the specified task.",
        specifier_input,
        [],
    )
    specified_task = specifier.text.strip()
    assistant_system, user_system = render_role_prompts(
        bundle,
        task=specified_task,
        assistant_role=assistant_role,
        user_role=user_role,
    )

    user_history: list[dict] = []
    assistant_history: list[dict] = []
    messages: list[ProtocolMessage] = []
    api_calls = specifier.api_calls
    tool_trace = list(specifier.tool_trace)
    tokens: dict[str, int] = {}

    def accumulate(result: TurnResult) -> None:
        nonlocal api_calls
        api_calls += result.api_calls
        tool_trace.extend(result.tool_trace)
        for key, value in result.tokens.items():
            if isinstance(value, int):
                tokens[key] = tokens.get(key, 0) + value

    for key, value in specifier.tokens.items():
        if isinstance(value, int):
            tokens[key] = tokens.get(key, 0) + value
    final_assistant = ""

    # Mirrors the historical RolePlaying initialization: the AI User receives
    # its role contract and an explicit instruction to begin with one
    # Instruction/Input pair.
    user_input = (
        f"{user_system}\n\nNow start with the first instruction. "
        "Reply only with Instruction and Input."
    )

    while len(messages) < PAPER_MESSAGE_LIMIT:
        user_result = turn("ai_user", user_system, user_input, user_history)
        user_history = user_result.history
        accumulate(user_result)
        user_text = user_result.text.strip()
        messages.append(
            ProtocolMessage(len(messages) + 1, "ai_user", user_text)
        )
        if is_exact_done(user_text):
            termination = "task_done"
            break
        if len(messages) >= PAPER_MESSAGE_LIMIT:
            termination = "message_limit"
            break

        assistant_result = turn(
            "ai_assistant",
            assistant_system,
            user_text,
            assistant_history,
        )
        assistant_history = assistant_result.history
        accumulate(assistant_result)
        final_assistant = assistant_result.text.strip()
        messages.append(
            ProtocolMessage(
                len(messages) + 1,
                "ai_assistant",
                final_assistant,
            )
        )
        user_input = final_assistant
    else:
        termination = "message_limit"

    run = CamelRun(
        original_task=original_task,
        specified_task=specified_task,
        assistant_role=assistant_role,
        user_role=user_role,
        messages=messages,
        termination=termination,
        final_assistant_text=final_assistant,
        prompt_hashes=bundle.hashes,
        api_calls=api_calls,
        tool_trace=tool_trace,
        tokens=tokens,
    )
    assert_conformant(run)
    return run
