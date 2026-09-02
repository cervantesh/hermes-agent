"""Create public V3 receipts with decision and redacted lifecycle evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
from datetime import datetime, timezone

from evals.shared_context_research.sanitize_evidence_v2 import (
    sanitize_fixture_v2,
    verify_sanitized_v2,
)

from .analysis_v3 import adjudicate_v3


def sanitize_fixture_v3(record: dict[str, Any]) -> dict[str, Any]:
    public = sanitize_fixture_v2(record)
    public["cohort"] = record["cohort"]
    public["remote_seal_source_commit"] = record["remote_seal_source_commit"]
    public["run_started_at_utc"] = record["run_started_at_utc"]
    public["public_lifecycle_events"] = record.get("public_lifecycle_events") or []
    return public


def sanitize_packet(
    raw_path: Path, output: Path, remote_seal_path: Path
) -> dict[str, Any]:
    raw = [
        json.loads(line)
        for line in raw_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rows = [sanitize_fixture_v3(row) for row in raw]
    verify_sanitized_v2(rows)
    output.mkdir(parents=True, exist_ok=True)
    observations = output / "observations.jsonl"
    observations.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    remote_seal = json.loads(remote_seal_path.read_text(encoding="utf-8"))
    published = datetime.fromisoformat(
        remote_seal["github_committed_at_utc"].replace("Z", "+00:00")
    ).astimezone(timezone.utc)
    if any(
        datetime.fromisoformat(
            row["run_started_at_utc"].replace("Z", "+00:00")
        ).astimezone(timezone.utc)
        < published
        for row in rows
    ):
        raise ValueError("observation predates remote seal publication")
    receipt = {
        "target_revision": rows[0]["target_head"],
        "observation_count": len(rows),
        "observations_sha256": hashlib.sha256(observations.read_bytes()).hexdigest(),
        "raw_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        "source_manifest_sha256": rows[0]["source_manifest_sha256"],
        "remote_seal": remote_seal,
        "decision": adjudicate_v3(rows),
    }
    (output / "receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--remote-seal",
        default=str(Path(__file__).with_name("REMOTE_SEAL_RECEIPT.json")),
    )
    args = parser.parse_args()
    print(
        json.dumps(
            sanitize_packet(
                Path(args.raw).resolve(),
                Path(args.output).resolve(),
                Path(args.remote_seal).resolve(),
            ),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
