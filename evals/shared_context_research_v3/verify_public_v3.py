"""Recompute, rather than trust, the V3 public decision."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from evals.shared_context_research.sanitize_evidence_v2 import verify_sanitized_v2

from .analysis_v3 import adjudicate_v3
from .protocol_v3 import COHORTS, PROVIDER, TARGET_REVISION


def verify_decision(
    rows: list[dict[str, Any]], receipt: dict[str, Any]
) -> dict[str, Any]:
    actual = adjudicate_v3(rows)
    if receipt.get("decision") != actual:
        raise ValueError("decision mismatch")
    return actual


def verify_chronology(rows: list[dict[str, Any]], receipt: dict[str, Any]) -> None:
    remote = receipt.get("remote_seal") or {}
    published = datetime.fromisoformat(
        remote["github_committed_at_utc"].replace("Z", "+00:00")
    ).astimezone(timezone.utc)
    for row in rows:
        started = datetime.fromisoformat(
            row["run_started_at_utc"].replace("Z", "+00:00")
        ).astimezone(timezone.utc)
        if started < published:
            raise ValueError("observation predates remote seal publication")
        if row.get("source_manifest_sha256") != receipt.get("source_manifest_sha256"):
            raise ValueError("observation source manifest mismatch")


def verify_packet(root: Path) -> dict[str, Any]:
    observations = root / "observations.jsonl"
    rows = [
        json.loads(line)
        for line in observations.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    receipt = json.loads((root / "receipt.json").read_text(encoding="utf-8"))
    digest = hashlib.sha256(observations.read_bytes()).hexdigest()
    if digest != receipt.get("observations_sha256"):
        raise ValueError("observation hash mismatch")
    if len(rows) != receipt.get("observation_count"):
        raise ValueError("observation count mismatch")
    verify_sanitized_v2(rows)
    if {row.get("target_head") for row in rows} != {TARGET_REVISION}:
        raise ValueError("unexpected target revision")
    if {row.get("provider") for row in rows} != {PROVIDER}:
        raise ValueError("unexpected provider")
    expected_models = {cohort.id: cohort.model for cohort in COHORTS}
    if any(expected_models.get(row.get("cohort")) != row.get("model") for row in rows):
        raise ValueError("cohort model mismatch")
    remote = receipt.get("remote_seal") or {}
    required_remote = {
        "repository",
        "source_commit",
        "github_commit_url",
        "github_committed_at_utc",
        "verified_at_utc",
        "source_manifest_sha256",
    }
    if not required_remote <= set(remote):
        raise ValueError("remote seal receipt incomplete")
    if remote.get("source_manifest_sha256") != receipt.get("source_manifest_sha256"):
        raise ValueError("remote seal source mismatch")
    if any(
        row.get("remote_seal_source_commit") != remote["source_commit"] for row in rows
    ):
        raise ValueError("observation remote seal mismatch")
    verify_chronology(rows, receipt)
    decision = verify_decision(rows, receipt)
    return {"ok": True, "count": len(rows), "sha256": digest, "decision": decision}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", required=True)
    args = parser.parse_args()
    print(json.dumps(verify_packet(Path(args.evidence_dir).resolve()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
