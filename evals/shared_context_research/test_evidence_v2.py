from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from .sanitize_evidence_v2 import sanitize_fixture_v2, verify_sanitized_v2
from .provenance_v2 import source_manifest_digest_v2, source_manifest_v2
from .verify_public_evidence_v2 import verify_packet_v2


def _raw_fixture() -> dict[str, object]:
    schema = {
        "profile": "consumer",
        "config_sha256": "c" * 64,
        "schema_sha256": "s" * 64,
        "tool_names": ["read_file", "kanban_show", "kanban_complete"],
        "forbidden_absent": True,
        "required_present": True,
        "surface_bounded": True,
    }
    arm = {
        "schedule_position": 1,
        "ok": True,
        "false_success": False,
        "scope_expansion": False,
        "handoff_fidelity": True,
        "consumer_checks": {"result_exact": True},
        "context_manifest": {},
        "context_receipts": [{"hop": "kanban_projection", "sha256": "h" * 64}],
        "trace_scope": {"ok": True, "resolved_paths": [r"C:\private\x"]},
        "parent_tokens": {"total_tokens": 0},
        "consumer_tokens": {"total_tokens": 10},
        "common_producer_tokens": 5,
        "total_tokens": 15,
        "cost_segments": {"constructed_total_seconds": 1.0},
        "duration_seconds": 1.0,
        "expected_digest": "e" * 64,
        "result_digest": "e" * 64,
        "profile_receipt": schema,
        "pre_run_counts": {"tasks": 1, "consumer_sessions": 0},
        "consumer": {
            "summary": "private",
            "log": r"C:\private\agent.log",
            "session_id": "secret-id",
            "tool_trace": [],
        },
        "consumer_files": ["result.json"],
    }
    return {
        "task": "compact_release_map",
        "schedule_seed": 377,
        "topology": "detached_source",
        "dependent": True,
        "preflight": True,
        "order": ["A", "B", "C"],
        "target_head": "1" * 40,
        "target_dirty": False,
        "provider": "provider",
        "model": "model",
        "producer": {"summary": "private", "log": r"C:\private\producer.log"},
        "producer_admitted": True,
        "producer_checks": {"digest_exact": True},
        "schemas_safe_equal": True,
        "schemas": {letter: schema for letter in "ABC"},
        "pre_run_counts": {letter: {"tasks": 0} for letter in "ABC"},
        "common_producer_tokens": 5,
        "common_producer_duration_seconds": 0.5,
        "arms": {
            letter: {**arm, "schedule_position": index}
            for index, letter in enumerate("ABC", 1)
        },
        "integrity": {"schemas_safe_equal": True},
        "provider_failure": None,
    }


def test_v2_sanitizer_drops_private_nested_fields() -> None:
    raw = _raw_fixture()
    raw["source_manifest_sha256"] = "m" * 64
    safe = sanitize_fixture_v2(raw)
    verify_sanitized_v2([safe])
    material = json.dumps(safe)
    assert "private" not in material
    assert '"session_id":' not in material
    assert "tool_trace" not in material
    assert "resolved_paths" not in material


def test_v2_verifier_rejects_path_shaped_material() -> None:
    raw = _raw_fixture()
    raw["source_manifest_sha256"] = "m" * 64
    safe = sanitize_fixture_v2(raw)
    poisoned = copy.deepcopy(safe)
    poisoned["integrity"]["note"] = r"C:\private\x"
    with pytest.raises(ValueError, match="path- or secret-shaped"):
        verify_sanitized_v2([poisoned])


def test_v2_public_packet_hash_is_verified(tmp_path: Path) -> None:
    source_root = Path(__file__).resolve().parent
    manifest = source_manifest_v2(source_root)
    assert "runtime.py" in manifest
    manifest_digest = source_manifest_digest_v2(manifest)
    raw = _raw_fixture()
    raw["source_manifest_sha256"] = manifest_digest
    safe = sanitize_fixture_v2(raw)
    observations = tmp_path / "observations.jsonl"
    observations.write_text(json.dumps(safe, sort_keys=True) + "\n", encoding="utf-8")
    import hashlib

    receipt = {
        "target_revision": "1" * 40,
        "observations_sha256": hashlib.sha256(observations.read_bytes()).hexdigest(),
        "observation_count": 1,
        "source_manifest": manifest,
        "source_manifest_sha256": manifest_digest,
    }
    (tmp_path / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    assert verify_packet_v2(tmp_path)["ok"] is True
    observations.write_text("{}\n", encoding="utf-8")
    with pytest.raises((ValueError, KeyError)):
        verify_packet_v2(tmp_path)
