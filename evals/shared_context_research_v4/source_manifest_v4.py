"""Decision-critical source binding for V4 and every reused kernel file."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from evals.shared_context_research_v3.source_manifest_v3 import source_manifest_v3


V4_FILES = (
    "PROTOCOL_FREEZE_V4.md",
    "RESEARCH_FRAME_V4.md",
    "fixture_worker_v4.py",
    "preflight_v4.py",
    "protocol_v4.py",
    "runner_v4.py",
    "sanitize_v4.py",
    "source_manifest_v4.py",
    "test_failure_retention_v4.py",
    "verify_public_v4.py",
)


def source_manifest_v4(root: Path) -> dict[str, str]:
    inherited = source_manifest_v3(root.parent / "shared_context_research_v3")
    own = {
        f"v4/{name}": hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in V4_FILES
    }
    return dict(sorted({**inherited, **own}.items()))


def manifest_digest_v4(manifest: dict[str, str]) -> str:
    encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()
