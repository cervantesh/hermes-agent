"""Tests for evidence extraction and immutable tree identification."""

from pathlib import Path
import subprocess

from runner import tree_id
from worker import _provider_failure, _tool_trace, _tokens


def test_tool_trace_extracts_only_assistant_calls() -> None:
    messages = [
        {"role": "user", "content": "x"},
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call-1",
                    "function": {"name": "exec_command", "arguments": "{}"},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call-1", "content": "ok"},
    ]
    assert _tool_trace(messages) == [{"name": "exec_command", "id": "call-1"}]


def test_tokens_rejects_non_integer_metadata() -> None:
    result = {"tokens": {"input": 3, "provider": "x", "estimated": 1.5}}
    assert _tokens(result) == {"input": 3}


def test_provider_failure_invalidates_observation() -> None:
    assert (
        _provider_failure(
            {
                "summary": "Gemini HTTP 429 (RESOURCE_EXHAUSTED): quota exceeded",
                "status": "failed",
            }
        )
        == "resource_exhausted"
    )
    assert _provider_failure({"summary": "completed", "error": None}) is None


def test_tree_id_changes_when_untracked_evidence_changes(tmp_path: Path) -> None:
    subprocess.check_call(["git", "init", "-q", str(tmp_path)])
    subprocess.check_call(["git", "-C", str(tmp_path), "config", "user.email", "eval@example.invalid"])
    subprocess.check_call(["git", "-C", str(tmp_path), "config", "user.name", "Eval"])
    tracked = tmp_path / "tracked.txt"
    tracked.write_text("stable\n", encoding="utf-8")
    subprocess.check_call(["git", "-C", str(tmp_path), "add", "tracked.txt"])
    subprocess.check_call(["git", "-C", str(tmp_path), "commit", "-qm", "base"])

    clean = tree_id(tmp_path)
    assert clean["dirty"] is False
    untracked = tmp_path / "observation.json"
    untracked.write_text("one\n", encoding="utf-8")
    first = tree_id(tmp_path)
    untracked.write_text("two\n", encoding="utf-8")
    second = tree_id(tmp_path)
    assert first["dirty"] is True
    assert first["tree_digest"] != second["tree_digest"]
