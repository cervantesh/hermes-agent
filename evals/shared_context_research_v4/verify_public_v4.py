"""Verify V4 public evidence and its retained failure receipts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evals.shared_context_research_v3.verify_public_v3 import verify_packet


def verify_packet_v4(root: Path) -> dict:
    result = verify_packet(root)
    rows = [
        json.loads(line)
        for line in (root / "observations.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line
    ]
    for row in rows:
        failure = row.get("fixture_failure")
        if failure is not None and set(failure) != {
            "exception_type",
            "failure_phase",
            "message_sha256",
        }:
            raise ValueError("unsafe or incomplete V4 fixture-failure receipt")
    result["fixture_failure_count"] = sum(
        row.get("fixture_failure") is not None for row in rows
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", required=True)
    args = parser.parse_args()
    print(
        json.dumps(verify_packet_v4(Path(args.evidence_dir).resolve()), sort_keys=True)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
