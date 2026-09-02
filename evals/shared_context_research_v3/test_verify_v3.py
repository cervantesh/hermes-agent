from __future__ import annotations

import json

import pytest

from evals.shared_context_research_v3.verify_public_v3 import (
    verify_chronology,
    verify_decision,
)


def test_verifier_rejects_mutated_decision(tmp_path) -> None:
    rows = []
    observations = tmp_path / "observations.jsonl"
    observations.write_text("", encoding="utf-8")
    receipt = tmp_path / "receipt.json"
    receipt.write_text(
        json.dumps({"decision": {"verdict": "IMPLEMENTATION OPPORTUNITY"}}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="decision mismatch"):
        verify_decision(rows, json.loads(receipt.read_text(encoding="utf-8")))


def test_verifier_rejects_observation_before_remote_publication() -> None:
    rows = [
        {
            "run_started_at_utc": "2026-09-02T01:59:59Z",
            "source_manifest_sha256": "a" * 64,
        }
    ]
    receipt = {
        "source_manifest_sha256": "a" * 64,
        "remote_seal": {"github_committed_at_utc": "2026-09-02T02:00:00Z"},
    }

    with pytest.raises(ValueError, match="predates remote seal"):
        verify_chronology(rows, receipt)
