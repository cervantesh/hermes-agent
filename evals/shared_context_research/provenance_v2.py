"""Decision-critical source manifest for V2 evidence binding."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


SOURCE_FILES_V2 = (
    "OWNERSHIP_AUDIT.md",
    "PILOT_V1_DISPOSITION.md",
    "PROTOCOL_ADVERSARIAL_REVIEW_V2.md",
    "PROTOCOL_FREEZE_V2.md",
    "analysis_v2.py",
    "fixture_worker_v2.py",
    "preflight_v2.py",
    "protocol_v2.py",
    "provenance_v2.py",
    "runner_v2.py",
    "runtime.py",
    "runtime_v2.py",
    "sanitize_evidence_v2.py",
    "shared_context.py",
    "tasks.py",
    "test_analysis_v2.py",
    "test_evidence_v2.py",
    "test_protocol_v2.py",
    "test_runtime_v2.py",
    "test_shared_context.py",
    "test_tasks.py",
    "verify_public_evidence_v2.py",
)


def source_manifest_v2(root: Path) -> dict[str, str]:
    return {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in SOURCE_FILES_V2
    }


def source_manifest_digest_v2(manifest: dict[str, str]) -> str:
    encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()
