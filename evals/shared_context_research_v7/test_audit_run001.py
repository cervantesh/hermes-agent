from __future__ import annotations

import json
from pathlib import Path

from .audit_run001 import audit


def test_published_run001_is_complete_but_protocol_invalid() -> None:
    journal = (
        Path(__file__).resolve().parent
        / "evidence"
        / "v7-scored-20260903"
        / "observations.jsonl"
    )
    rows = [
        json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines()
    ]

    result = audit(rows)

    assert result["observation_count"] == 23
    assert result["slots_complete"] is True
    assert result["provider_usage_complete"] is True
    assert result["track2_expansion_expected"] is True
    assert result["d_rows_with_forbidden_kanban_tools"] == 8
    assert result["all_records_controls_exact"] is False
    assert result["track3_positive_controls_exact"] is False
    assert result["canary_disclosed_in_any_track3_prompt"] is False
    assert result["disposition"] == "INCONCLUSIVE_PROTOCOL_IMPLEMENTATION"
    assert result["reuse_policy"] == "PRESERVE_BUT_DO_NOT_POOL_WITH_A_REPETITION"
