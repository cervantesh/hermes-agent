from pathlib import Path

import pytest

from camel_protocol import (
    CamelRun,
    PAPER_CAMEL_COMMIT,
    PAPER_MESSAGE_LIMIT,
    ProtocolMessage,
    TASK_DONE,
    TurnResult,
    assert_conformant,
    is_exact_done,
    load_paper_prompts,
    render_role_prompts,
    run_role_playing,
)


CAMEL_REPO = Path("C:/dev/camel-audit")


def test_loads_exact_paper_era_prompt_sources():
    bundle = load_paper_prompts(CAMEL_REPO)

    assert bundle.source_commit == PAPER_CAMEL_COMMIT
    assert set(bundle.hashes) == {"specifier", "assistant", "user"}
    assert all(len(value) == 64 for value in bundle.hashes.values())
    assert "<CAMEL_TASK_DONE>" in bundle.user


def test_role_prompts_receive_same_specified_task_and_roles():
    bundle = load_paper_prompts(CAMEL_REPO)
    assistant, user = render_role_prompts(
        bundle,
        task="Produce the exact release receipt",
        assistant_role="Release Engineer",
        user_role="Release Manager",
    )

    for prompt in (assistant, user):
        assert "Produce the exact release receipt" in prompt
        assert "Release Engineer" in prompt
        assert "Release Manager" in prompt
    assert "<ASSISTANT_ROLE>" not in assistant + user
    assert "<USER_ROLE>" not in assistant + user
    assert "<TASK>" not in assistant + user


def test_exact_done_does_not_accept_prose_or_assistant_claims():
    assert is_exact_done(TASK_DONE)
    assert not is_exact_done(f"Done: {TASK_DONE}")
    assert not is_exact_done("The task is complete")


def test_protocol_alternates_and_only_user_terminates():
    bundle = load_paper_prompts(CAMEL_REPO)
    replies = iter(
        [
            "Create an exact artifact",
            "Instruction: create output.txt\nInput: VALUE=ok",
            "Solution: created output.txt. Next request.",
            TASK_DONE,
        ]
    )

    def turn(role, system, message, history):
        text = next(replies)
        return TurnResult(
            text=text,
            history=[*history, {"role": "user", "content": message}, {"role": "assistant", "content": text}],
        )

    run = run_role_playing(
        original_task="Create the deliverable",
        assistant_role="Engineer",
        user_role="Owner",
        bundle=bundle,
        turn=turn,
    )

    assert run.termination == "task_done"
    assert [message.speaker for message in run.messages] == [
        "ai_user",
        "ai_assistant",
        "ai_user",
    ]
    assert run.messages[-1].content == TASK_DONE
    assert run.api_calls == 4


def test_message_limit_is_exactly_forty_role_messages():
    bundle = load_paper_prompts(CAMEL_REPO)
    calls = 0

    def turn(role, system, message, history):
        nonlocal calls
        calls += 1
        if role == "task_specifier":
            text = "Complete the bounded task"
        elif role == "ai_user":
            text = "Instruction: continue\nInput: None"
        else:
            text = "Solution: progress. Next request."
        return TurnResult(text=text, history=[])

    run = run_role_playing(
        original_task="Complete the task",
        assistant_role="Engineer",
        user_role="Owner",
        bundle=bundle,
        turn=turn,
    )

    assert run.termination == "message_limit"
    assert len(run.messages) == PAPER_MESSAGE_LIMIT
    assert calls == PAPER_MESSAGE_LIMIT + 1


def test_conformance_rejects_assistant_owned_termination():
    run = CamelRun(
        original_task="x",
        specified_task="x",
        assistant_role="a",
        user_role="u",
        messages=[
            ProtocolMessage(1, "ai_user", "Instruction: work\nInput: None"),
            ProtocolMessage(2, "ai_assistant", TASK_DONE),
        ],
        termination="task_done",
        final_assistant_text=TASK_DONE,
        prompt_hashes={},
        api_calls=2,
    )

    with pytest.raises(AssertionError, match="AI User"):
        assert_conformant(run)
