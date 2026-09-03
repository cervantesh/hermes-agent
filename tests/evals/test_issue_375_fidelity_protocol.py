from dataclasses import dataclass

from evals.issue_375_fidelity_research.protocol import (
    Generation,
    RolePrompts,
    run_role_play,
)


@dataclass
class ScriptedBackend:
    outputs: list[str]

    def __post_init__(self):
        self.calls = []

    def complete(self, *, agent, system_prompt, messages, parameters):
        self.calls.append({
            "agent": agent,
            "system_prompt": system_prompt,
            "messages": [dict(message) for message in messages],
            "parameters": dict(parameters),
        })
        return Generation(text=self.outputs.pop(0), finish_reason="stop", usage={})


def _prompts():
    return RolePrompts(assistant="assistant system", user="user system")


def test_historical_hidden_assistant_priming_is_executed_and_discarded():
    backend = ScriptedBackend([
        "hidden priming output",
        "Instruction: first\nInput: None",
        "Solution: first\nNext request.",
        "<CAMEL_TASK_DONE>",
        "Solution: ignored by stop check\nNext request.",
    ])

    result = run_role_play(_prompts(), backend, max_role_messages=40)

    assert backend.calls[0]["agent"] == "assistant"
    assert backend.calls[0]["messages"] == [
        {"role": "user", "content": "assistant system"}
    ]
    assert backend.calls[1]["agent"] == "user"
    assert backend.calls[1]["messages"][0]["content"].endswith(
        "Only reply with Instruction and Input."
    )
    assert "hidden priming output" not in [
        message["content"] for message in result.transcript
    ]
    assert result.termination_reason == "<CAMEL_TASK_DONE>"
    assert result.num_role_messages == 3


def test_each_agent_history_strictly_alternates_user_and_assistant():
    backend = ScriptedBackend([
        "hidden",
        "Instruction: one\nInput: None",
        "Solution: one\nNext request.",
        "Instruction: two\nInput: None",
        "Solution: two\nNext request.",
    ])

    run_role_play(_prompts(), backend, max_role_messages=4)

    for call in backend.calls:
        assert [message["role"] for message in call["messages"]] == [
            "user" if index % 2 == 0 else "assistant"
            for index in range(len(call["messages"]))
        ]


def test_three_user_messages_without_instruction_terminate_conversation():
    backend = ScriptedBackend([
        "hidden",
        "not an instruction 1",
        "solution 1",
        "not an instruction 2",
        "solution 2",
        "not an instruction 3",
        "solution 3",
    ])

    result = run_role_play(_prompts(), backend, max_role_messages=40)

    assert result.termination_reason == "user_no_instruct_threshold"
    assert result.num_role_messages == 4


def test_assistant_instruction_role_flip_terminates_before_messages_are_saved():
    backend = ScriptedBackend(
        ["hidden", "Instruction: valid\nInput: None", "Instruction: flipped"],
    )

    result = run_role_play(_prompts(), backend, max_role_messages=40)

    assert result.termination_reason == "assistant_instruct_threshold"
    assert result.num_role_messages == 0


def test_repeat_word_threshold_matches_historical_loop():
    backend = ScriptedBackend([
        "hidden",
        "Instruction: goodbye, good bye, and thank\nInput: None",
        "Solution: one",
    ])

    result = run_role_play(_prompts(), backend, max_role_messages=40)

    assert result.termination_reason == "repeat_word_threshold"


def test_role_message_cap_is_exactly_forty():
    outputs = ["hidden"]
    for index in range(20):
        outputs.extend([
            f"Instruction: step {index}\nInput: None",
            f"Solution: step {index}\nNext request.",
        ])
    backend = ScriptedBackend(outputs)

    result = run_role_play(_prompts(), backend, max_role_messages=40)

    assert result.termination_reason == "max_num_messages"
    assert result.num_role_messages == 40


def test_historical_token_guard_stops_before_provider_call():
    backend = ScriptedBackend([])

    result = run_role_play(
        _prompts(),
        backend,
        max_role_messages=40,
        token_counter=lambda messages: 4096,
        token_limit=4096,
    )

    assert backend.calls == []
    assert result.termination_reason == "assistant: max_tokens_exceeded"


def test_each_role_request_is_capped_to_remaining_historical_context():
    backend = ScriptedBackend([
        "hidden",
        "<CAMEL_TASK_DONE>",
        "unused assistant output",
    ])

    run_role_play(
        _prompts(),
        backend,
        token_counter=lambda messages: 1000,
        token_limit=4096,
    )

    assert all(call["parameters"]["max_tokens"] == 3096 for call in backend.calls)
