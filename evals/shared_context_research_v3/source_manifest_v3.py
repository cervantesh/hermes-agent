"""Decision-critical source binding for V3."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


V3_FILES = (
    "PROTOCOL_FREEZE_V3.md",
    "RESEARCH_FRAME_V3.md",
    "TARGET_REFRESH_V3.md",
    "analysis_v3.py",
    "durable_reader_v3.py",
    "fixture_worker_v3.py",
    "preflight_v3.py",
    "protocol_v3.py",
    "runner_v3.py",
    "runtime_v3.py",
    "sanitize_v3.py",
    "source_manifest_v3.py",
    "test_durable_context_v3.py",
    "test_protocol_v3.py",
    "test_verify_v3.py",
    "verify_public_v3.py",
)

REUSED_V2_FILES = (
    "analysis_v2.py",
    "protocol_v2.py",
    "runtime.py",
    "runtime_v2.py",
    "sanitize_evidence_v2.py",
    "shared_context.py",
    "tasks.py",
)


def source_manifest_v3(root: Path) -> dict[str, str]:
    parent = root.parent / "shared_context_research"
    files = {
        f"v3/{name}": hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in V3_FILES
    }
    files.update({
        f"v2/{name}": hashlib.sha256((parent / name).read_bytes()).hexdigest()
        for name in REUSED_V2_FILES
    })
    return dict(sorted(files.items()))


def manifest_digest_v3(manifest: dict[str, str]) -> str:
    encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()
