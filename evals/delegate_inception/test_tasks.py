"""Regression tests for provider-neutral delegation-eval oracles."""

from evals.delegate_inception.tasks import TASKS_BY_ID, _recovery_grade


def test_prompts_do_not_embed_the_candidate_execution_contract():
    prompts = "\n".join(task.prompt.lower() for task in TASKS_BY_ID.values())

    assert "retry it once" not in prompts
    assert "if the same failure repeats" not in prompts
    assert "report the result and any blocker precisely" not in prompts
    assert "report the exact file and both relevant values" not in prompts


def _grade_with_transcript(tmp_path, tool_name: str) -> dict[str, bool]:
    (tmp_path / "recovery.txt").write_text(
        "RECOVERY_TOKEN=violet-42\n", encoding="utf-8"
    )
    transcript = "\n".join(
        [
            f"00:00:01 tool     | -> {tool_name}(python scripts/probe.py)",
            f"00:00:02 tool     | -> {tool_name}(python scripts/probe.py)",
        ]
    )
    return _recovery_grade(
        "Recovered violet-42",
        {"tool_trace": [{"tool": tool_name}], "_eval_transcript": transcript},
        tmp_path,
    )


def test_recovery_oracle_counts_hermes_terminal_calls(tmp_path):
    checks = _grade_with_transcript(tmp_path, "terminal")

    assert all(checks.values())


def test_recovery_oracle_counts_codex_exec_calls(tmp_path):
    checks = _grade_with_transcript(tmp_path, "exec_command")

    assert all(checks.values())
