from __future__ import annotations

import json
from pathlib import Path

import pytest

from .evidence import (
    EvidenceLedger,
    build_manifest,
    digest_file,
    sanitize_observation,
    verify_seal,
)


def test_manifest_hashes_bytes_and_uses_relative_names(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_bytes(b"alpha\n")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "b.txt").write_bytes(b"beta\n")

    manifest = build_manifest(tmp_path, ("a.txt", "nested/b.txt"))

    assert tuple(manifest) == ("a.txt", "nested/b.txt")
    assert manifest["a.txt"] == digest_file(tmp_path / "a.txt")


def test_seal_verification_detects_source_drift(tmp_path: Path) -> None:
    source = tmp_path / "protocol.md"
    source.write_text("frozen\n", encoding="utf-8")
    seal = tmp_path / "seal.json"
    seal.write_text(
        json.dumps({"manifest": {"protocol.md": digest_file(source)}}),
        encoding="utf-8",
    )

    verify_seal(tmp_path, seal)
    source.write_text("changed\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="seal mismatch"):
        verify_seal(tmp_path, seal)


def test_evidence_ledger_retains_failure_and_refuses_replacement(
    tmp_path: Path,
) -> None:
    ledger = EvidenceLedger.create(tmp_path, "run-001")
    ledger.append({"slot": 1, "status": "provider_failure"})
    ledger.abort({"slot": 1, "reason": "timeout"})

    assert ledger.rows_path.read_text(encoding="utf-8").count("\n") == 1
    assert ledger.abort_path.is_file()
    with pytest.raises(FileExistsError):
        EvidenceLedger.create(tmp_path, "run-001")


def test_public_sanitizer_is_allowlist_based() -> None:
    raw = {
        "track": "context_cost",
        "arm": "B",
        "cohort": "model-a",
        "seed": 377,
        "external_oracle": True,
        "prompt_bytes": 100,
        "input_tokens": 20,
        "latency_ms": 30,
        "result_digest": "abc",
        "tool_counts": {"kanban_show": 1},
        "api_key": "must-not-leak",
        "raw_prompt": "private",
        "host_path": "C:/private/user",
    }

    public = sanitize_observation(raw)

    assert public == {
        "track": "context_cost",
        "arm": "B",
        "cohort": "model-a",
        "seed": 377,
        "external_oracle": True,
        "prompt_bytes": 100,
        "input_tokens": 20,
        "latency_ms": 30,
        "result_digest": "abc",
        "tool_counts": {"kanban_show": 1},
    }
