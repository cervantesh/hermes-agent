from __future__ import annotations

import json

from .common.evidence import digest_file, verify_seal
from .source_manifest import ROOT


def test_design_and_protocol_seals_match_active_bytes() -> None:
    design = json.loads((ROOT / "DESIGN_SEAL.json").read_text(encoding="utf-8"))
    assert digest_file(ROOT / "INITIAL_DESIGN_FREEZE.md") == design["design_sha256"]
    verify_seal(ROOT, ROOT / "PROTOCOL_SEAL.json")
