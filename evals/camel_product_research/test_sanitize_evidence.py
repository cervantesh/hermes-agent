import json

from sanitize_evidence import export, sanitize_record


def test_sanitize_record_keeps_oracles_and_drops_transcripts() -> None:
    record = {
        "task": "simple_manifest",
        "ok": False,
        "checks": {"manifest_exact": False},
        "repo": "C:/private/repo",
        "summary": "private model prose",
        "protocol": {
            "specified_task": "Write the artifact",
            "termination": "task_done",
            "message_count": 3,
            "prompt_hashes": {"user": "abc"},
            "messages": [{"content": "private transcript"}],
        },
    }
    result = sanitize_record(record)
    assert result["checks"] == {"manifest_exact": False}
    assert result["protocol"]["specified_task"] == "Write the artifact"
    assert "repo" not in result
    assert "summary" not in result
    assert "messages" not in result["protocol"]


def test_export_writes_hash_linked_receipts(tmp_path) -> None:
    source = tmp_path / "raw.jsonl"
    output = tmp_path / "evidence.jsonl"
    source.write_text(
        json.dumps({"task": "a", "protocol": None, "repo": "C:/private"}) + "\n",
        encoding="utf-8",
    )
    metadata = export(source, output)
    exported = json.loads(output.read_text(encoding="utf-8"))
    assert exported["task"] == "a"
    assert "repo" not in exported
    assert metadata["records"] == 1
    assert output.with_suffix(".meta.json").is_file()
