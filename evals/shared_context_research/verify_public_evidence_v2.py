"""Verify a V2 public evidence packet without reading private observations."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .provenance_v2 import source_manifest_digest_v2, source_manifest_v2
from .sanitize_evidence_v2 import verify_sanitized_v2


EVAL_DIR = Path(__file__).resolve().parent


def verify_packet_v2(root: Path, source_root: Path = EVAL_DIR) -> dict[str, object]:
    observations = root / "observations.jsonl"
    meta = json.loads((root / "receipt.json").read_text(encoding="utf-8"))
    rows = [
        json.loads(line)
        for line in observations.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    verify_sanitized_v2(rows)
    actual = hashlib.sha256(observations.read_bytes()).hexdigest()
    if actual != meta["observations_sha256"]:
        raise ValueError("observation receipt hash mismatch")
    if len(rows) != meta["observation_count"]:
        raise ValueError("observation count mismatch")
    if {row["target_head"] for row in rows} != {meta["target_revision"]}:
        raise ValueError("target revision mismatch")
    current_manifest = source_manifest_v2(source_root)
    if current_manifest != meta.get("source_manifest"):
        raise ValueError("source manifest differs from the evidence frame")
    digest = source_manifest_digest_v2(current_manifest)
    if digest != meta.get("source_manifest_sha256"):
        raise ValueError("source manifest digest mismatch")
    if {row.get("source_manifest_sha256") for row in rows} != {digest}:
        raise ValueError("observation provenance digest mismatch")
    return {"ok": True, "count": len(rows), "sha256": actual}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", required=True)
    parser.add_argument("--source-root")
    args = parser.parse_args()
    source_root = Path(args.source_root).resolve() if args.source_root else EVAL_DIR
    print(json.dumps(verify_packet_v2(Path(args.evidence_dir).resolve(), source_root)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
