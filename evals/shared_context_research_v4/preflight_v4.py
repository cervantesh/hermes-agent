"""Run the frozen unscored V4 provider/topology preflight."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from types import SimpleNamespace

from evals.shared_context_research.protocol_v2 import PREFLIGHT_ONLY

from .protocol_v4 import COHORTS, PROVIDER
from .runner_v4 import (
    PREFLIGHT_PASS,
    ROOT,
    _run_fixture,
    verify_remote_seal_v4,
    verify_seal_v4,
)
from .sanitize_v4 import sanitize_fixture_v4
from .source_manifest_v4 import source_manifest_v4


def _valid(record: dict) -> bool:
    integrity = record.get("integrity") or {}
    return (
        record.get("preflight") is True
        and not record.get("provider_failure")
        and not record.get("fixture_failure")
        and record.get("producer_admitted") is True
        and set(record.get("arms") or {}) == {"A", "B", "C"}
        and bool(integrity)
        and all(value is True for value in integrity.values())
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--python-executable", required=True)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    seal = verify_seal_v4()
    remote = verify_remote_seal_v4(seal)
    cohort = COHORTS[0]
    private = ROOT / "results-private" / args.label / "preflight-v4.jsonl"
    public = ROOT / "evidence" / args.label
    if private.exists() or public.exists():
        raise SystemExit("refusing to overwrite an existing V4 preflight")
    private.parent.mkdir(parents=True, exist_ok=True)
    runner_args = SimpleNamespace(
        repo_root=args.repo_root, python_executable=args.python_executable
    )
    rows = []
    for task in PREFLIGHT_ONLY:
        if source_manifest_v4(ROOT) != seal["source_manifest"]:
            raise SystemExit("decision-critical V4 source changed during preflight")
        started = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        record, attempts = _run_fixture(runner_args, cohort, task, preflight=True)
        record.update({
            "cohort": cohort.id,
            "model": cohort.model,
            "provider": PROVIDER,
            "attempts": attempts,
            "protocol_sha256": seal["protocol_sha256"],
            "source_manifest_sha256": seal["source_manifest_sha256"],
            "remote_seal_source_commit": remote["source_commit"],
            "run_started_at_utc": started,
        })
        rows.append(record)
    private.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    if not all(_valid(row) for row in rows):
        raise SystemExit("unscored V4 preflight failed; private evidence retained")
    public.mkdir(parents=True)
    observations = public / "observations.jsonl"
    observations.write_text(
        "".join(
            json.dumps(sanitize_fixture_v4(row), sort_keys=True) + "\n" for row in rows
        ),
        encoding="utf-8",
    )
    receipt = {
        "kind": "unscored_provider_topology_preflight_v4",
        "target_revision": rows[0]["target_head"],
        "cohort": cohort.id,
        "fixtures": list(PREFLIGHT_ONLY),
        "evidence_label": args.label,
        "observation_count": len(rows),
        "observations_sha256": hashlib.sha256(observations.read_bytes()).hexdigest(),
        "source_manifest_sha256": seal["source_manifest_sha256"],
        "remote_seal_source_commit": remote["source_commit"],
        "passed": True,
    }
    encoded = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    (public / "receipt.json").write_text(encoded, encoding="utf-8")
    PREFLIGHT_PASS.write_text(encoded, encoding="utf-8")
    print(json.dumps({"receipt": receipt, "evidence_dir": str(public)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
