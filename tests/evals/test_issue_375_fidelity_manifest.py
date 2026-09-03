import json

import pytest

from evals.issue_375_fidelity_research.manifest import (
    build_sample_manifest,
    resolve_manifest,
)


def _row(record_id: str, message_id: int, **overrides):
    row = {
        "id": record_id,
        "input": "historical input must not be used",
        "instruction": "historical instruction must not be used",
        "original_task": f"original {record_id}",
        "output": "historical output must not be used",
        "role_1": "Programmer_RoleType.ASSISTANT",
        "role_1_message_id": message_id,
        "role_1_response": "historical response must not be used",
        "role_2": "Filmmaker_RoleType.USER",
        "specified_task": f"specified {record_id}",
        "termination_reason": "historical termination must not be used",
    }
    row.update(overrides)
    return row


def test_manifest_selects_distinct_conversations_and_contains_only_hashes(tmp_path):
    source = tmp_path / "ai_society.json"
    source.write_text(
        json.dumps([_row("b", 1), _row("a", 1), _row("a", 2), _row("c", 1)]),
        encoding="utf-8",
    )

    manifest = build_sample_manifest(source, sample_size=2, seed="frozen-seed")

    assert manifest["sample_size"] == 2
    assert len({record["id"] for record in manifest["records"]}) == 2
    assert all(
        set(record)
        == {
            "id",
            "rank_sha256",
            "original_task_sha256",
            "specified_task_sha256",
            "assistant_role_sha256",
            "user_role_sha256",
        }
        for record in manifest["records"]
    )
    serialized = json.dumps(manifest)
    assert "historical" not in serialized
    assert "specified a" not in serialized


def test_manifest_resolves_pinned_fields_without_historical_messages(tmp_path):
    source = tmp_path / "ai_society.json"
    source.write_text(json.dumps([_row("a", 1), _row("a", 2)]), encoding="utf-8")
    manifest = build_sample_manifest(source, sample_size=1, seed="frozen-seed")

    resolved = resolve_manifest(source, manifest)

    assert resolved == [
        {
            "id": "a",
            "original_task": "original a",
            "specified_task": "specified a",
            "assistant_role": "Programmer",
            "user_role": "Filmmaker",
        }
    ]


def test_manifest_rejects_inconsistent_fields_within_conversation(tmp_path):
    source = tmp_path / "ai_society.json"
    source.write_text(
        json.dumps([_row("a", 1), _row("a", 2, specified_task="changed")]),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="inconsistent.*specified_task"):
        build_sample_manifest(source, sample_size=1, seed="frozen-seed")
