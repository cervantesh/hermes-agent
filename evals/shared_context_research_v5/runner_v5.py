"""No-replacement two-stage runner for V5."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from .protocol_v5 import (
    CONFIRMATION_COHORTS,
    GATE_COHORT,
    PROVIDER,
    TASK_IDS,
    gate_passes,
)
from .source_manifest_v5 import manifest


ROOT = Path(__file__).resolve().parent


def _verify_seals() -> tuple[dict, dict]:
    seal = json.loads((ROOT / "PROTOCOL_SEAL_V5.json").read_text(encoding="utf-8"))
    current = manifest()
    if seal.get("source_manifest") != current:
        raise RuntimeError("V5 source differs from the prospective seal")
    digest = hashlib.sha256(
        json.dumps(current, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if seal.get("source_manifest_sha256") != digest:
        raise RuntimeError("V5 source-manifest digest mismatch")
    remote = json.loads(
        (ROOT / "REMOTE_SEAL_RECEIPT_V5.json").read_text(encoding="utf-8")
    )
    if remote.get("source_manifest_sha256") != digest:
        raise RuntimeError("V5 remote seal does not bind the active source")
    committed = datetime.fromisoformat(
        str(remote["github_committed_at_utc"]).replace("Z", "+00:00")
    ).astimezone(timezone.utc)
    if committed > datetime.now(timezone.utc):
        raise RuntimeError("V5 remote seal timestamp is in the future")
    committed_seal = subprocess.check_output(
        [
            "git",
            "show",
            f"{remote['source_commit']}:evals/shared_context_research_v5/PROTOCOL_SEAL_V5.json",
        ],
        cwd=ROOT,
        text=True,
    )
    if json.loads(committed_seal) != seal:
        raise RuntimeError("V5 remote commit does not contain the active seal")
    return seal, remote


def _run(args, *, phase: str, cohort: dict, task: str) -> dict:
    command = [
        sys.executable,
        "-m",
        "evals.shared_context_research_v5.fixture_worker_v5",
        "--phase",
        phase,
        "--repo-root",
        args.repo_root,
        "--python-executable",
        args.python_executable,
        "--task",
        task,
        "--seed",
        str(cohort["seed"]),
        "--model",
        cohort["model"],
        "--provider",
        PROVIDER,
    ]
    completed = subprocess.run(
        command, check=True, capture_output=True, text=True, encoding="utf-8"
    )
    row = json.loads(completed.stdout.strip().splitlines()[-1])
    row["cohort"] = cohort["id"]
    return row


def _write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--python-executable", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    _verify_seals()
    output = Path(args.output).resolve()
    if output.exists():
        raise SystemExit("V5 output already exists; replacement is forbidden")
    rows = [
        _run(args, phase="gate", cohort=GATE_COHORT, task=task) for task in TASK_IDS
    ]
    _write(output, rows)
    if not gate_passes(rows):
        print(json.dumps({"expanded": False, "reason": "B gate did not pass"}))
        return 0
    for cohort in (GATE_COHORT, *CONFIRMATION_COHORTS):
        for task in TASK_IDS:
            rows.append(_run(args, phase="comparison", cohort=cohort, task=task))
            _write(output, rows)
    print(json.dumps({"expanded": True, "observation_count": len(rows)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
