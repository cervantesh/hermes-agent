from __future__ import annotations

import json
from pathlib import Path

from evals.shared_context_research.runtime import _json_block
from evals.shared_context_research.tasks import TASKS_BY_ID

from .audit_handoff_semantics_v4 import _sha, audit_rows


def _row(summary: str, *, wrapper_exact: bool) -> dict:
    return {
        "dependent": True,
        "cohort": "test-cohort",
        "task": "compact_release_map",
        "producer": {"summary": summary},
        "arms": {"B": {"handoff_fidelity": wrapper_exact, "ok": True}},
    }


def test_canonical_json_without_wrapper_is_semantically_exact() -> None:
    source = TASKS_BY_ID["compact_release_map"].source
    summary = (
        _json_block(source)
        .removeprefix("<handoff-json>")
        .removesuffix("</handoff-json>")
    )

    [receipt] = audit_rows([_row(summary, wrapper_exact=False)])

    assert receipt["wrapper_exact_recorded"] is False
    assert receipt["parseable_json"] is True
    assert receipt["semantic_equal"] is True
    assert receipt["normalized_payload_sha256"] == receipt["expected_source_sha256"]


def test_wrapped_canonical_json_remains_semantically_exact() -> None:
    source = TASKS_BY_ID["compact_release_map"].source

    [receipt] = audit_rows([_row(_json_block(source), wrapper_exact=True)])

    assert receipt["wrapper_exact_recorded"] is True
    assert receipt["semantic_equal"] is True


def test_parseable_but_changed_json_is_not_semantically_exact() -> None:
    [receipt] = audit_rows([_row('{"changed":true}', wrapper_exact=False)])

    assert receipt["parseable_json"] is True
    assert receipt["semantic_equal"] is False


def test_published_receipt_is_internally_verifiable() -> None:
    receipt_path = (
        Path(__file__).parent
        / "evidence"
        / "issue377-v4-handoff-semantic-audit-20260902"
        / "receipt.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

    assert receipt["dependent_observation_count"] == 12
    assert receipt["semantic_exact_count"] == 12
    assert receipt["wrapper_exact_count"] == 8
    assert len(receipt["rows"]) == 12

    for row in receipt["rows"]:
        expected_sha = _sha(
            json.dumps(
                TASKS_BY_ID[row["task"]].source,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        )
        assert row["semantic_equal"] is True
        assert row["parseable_json"] is True
        assert row["normalized_payload_sha256"] == expected_sha
        assert row["expected_source_sha256"] == expected_sha
