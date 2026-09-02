from __future__ import annotations

import json

import pytest

from .runner import verify_seal
from .sanitize_evidence import sanitize_record, verify_sanitized


def test_protocol_seal_is_intact() -> None:
    assert verify_seal()["target_revision"].startswith("180291162f")


def test_sanitizer_drops_private_fields() -> None:
    raw = {
        "task": "x",
        "arm": "B",
        "topology": "detached_source",
        "dependent": True,
        "schedule_seed": 377,
        "model": "m",
        "provider": "p",
        "target_head": "h",
        "protocol_sha256": "s",
        "ok": True,
        "false_success": False,
        "scope_expansion": False,
        "handoff_fidelity": True,
        "producer": {
            "summary": "private",
            "log": "C:\\secret",
            "checks": {"x": True},
            "tokens": {},
        },
        "consumer": {"summary": "private", "checks": {"y": True}, "tokens": {}},
        "context_receipts": [],
        "parent_tokens": {},
        "total_tokens": 1,
        "duration_seconds": 1,
        "expected_digest": "a",
        "result_digest": "a",
    }
    clean = sanitize_record(raw)
    material = json.dumps(clean)
    assert "private" not in material
    assert "C:\\secret" not in material


def test_sanitized_verifier_rejects_path_material() -> None:
    row = {
        "target_head": "h",
        "protocol_sha256": "s",
        "model": "m",
        "provider": "p",
        "task": "C:\\leak",
        "arm": "A",
    }
    with pytest.raises(ValueError, match="path or secret"):
        verify_sanitized([row])
