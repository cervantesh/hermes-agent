"""Verify the sanitized packet without access to private provider traces."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .sanitize_evidence import verify_sanitized


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", required=True)
    args = parser.parse_args()
    root = Path(args.evidence_dir).resolve()
    receipt_path = root / "observations.jsonl"
    meta = json.loads((root / "receipt.json").read_text(encoding="utf-8"))
    rows = [
        json.loads(line)
        for line in receipt_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    verify_sanitized(rows)
    actual = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    if actual != meta["observations_sha256"]:
        raise SystemExit("observation receipt hash mismatch")
    if len(rows) != meta["observation_count"]:
        raise SystemExit("observation count mismatch")
    print(json.dumps({"ok": True, "count": len(rows), "sha256": actual}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
