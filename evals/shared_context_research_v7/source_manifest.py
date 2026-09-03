"""Files whose bytes define V7 scored observations."""

from __future__ import annotations

from .common.evidence import build_manifest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FILES = (
    "INITIAL_DESIGN_FREEZE.md",
    "DESIGN_SEAL.json",
    "CAMEL_REFERENCE_CONTRACT.md",
    "OWNERSHIP_AUDIT.md",
    "protocol.py",
    "scored_runner.py",
    "source_manifest.py",
    "seal_protocol.py",
    "common/evidence.py",
    "common/harness.py",
    "common/hermes_fixture.py",
    "common/model_runtime.py",
    "common/preflight_runner.py",
    "context_cost/PROTOCOL_FREEZE.md",
    "context_cost/preflight.py",
    "context_cost/runner.py",
    "isolation/PROTOCOL_FREEZE.md",
    "isolation/preflight.py",
    "isolation/runner.py",
    "selective_access/PROTOCOL_FREEZE.md",
    "selective_access/preflight.py",
    "selective_access/runner.py",
)


def manifest() -> dict[str, str]:
    return build_manifest(ROOT, FILES)
