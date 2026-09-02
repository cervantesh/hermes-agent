"""Crash-visible, no-replacement two-stage runner for V6."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from .protocol_v6 import (
    CONFIRMATION_COHORTS,
    GATE_COHORT,
    PROVIDER,
    TASK_IDS,
    gate_passes,
)
from .source_manifest_v6 import manifest


ROOT = Path(__file__).resolve().parent


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def _write_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    temporary.replace(path)


def _verify_seals() -> None:
    seal = json.loads((ROOT / "PROTOCOL_SEAL_V6.json").read_text(encoding="utf-8"))
    current = manifest()
    digest = _digest(json.dumps(current, sort_keys=True, separators=(",", ":")))
    if (
        seal.get("source_manifest") != current
        or seal.get("source_manifest_sha256") != digest
    ):
        raise RuntimeError("V6 source differs from the prospective seal")
    remote = json.loads(
        (ROOT / "REMOTE_SEAL_RECEIPT_V6.json").read_text(encoding="utf-8")
    )
    if remote.get("source_manifest_sha256") != digest:
        raise RuntimeError("V6 remote seal does not bind the active source")
    committed = datetime.fromisoformat(
        str(remote["github_committed_at_utc"]).replace("Z", "+00:00")
    ).astimezone(timezone.utc)
    if committed > datetime.now(timezone.utc):
        raise RuntimeError("V6 remote seal timestamp is in the future")
    committed_seal = subprocess.check_output(
        [
            "git",
            "show",
            f"{remote['source_commit']}:evals/shared_context_research_v6/PROTOCOL_SEAL_V6.json",
        ],
        cwd=ROOT,
        text=True,
    )
    if json.loads(committed_seal) != seal:
        raise RuntimeError("V6 remote commit does not contain the active seal")


def _command(args, *, phase: str, cohort: dict, task: str) -> list[str]:
    return [
        sys.executable,
        "-m",
        "evals.shared_context_research_v6.fixture_worker_v6",
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


def _run_slot(args, *, phase: str, cohort: dict, task: str) -> dict:
    command = _command(args, phase=phase, cohort=cohort, task=task)
    completed = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8"
    )
    if completed.returncode != 0:
        return {
            "phase": phase,
            "cohort": cohort["id"],
            "task": task,
            "fixture_failure": {
                "type": "subprocess_nonzero",
                "returncode": completed.returncode,
                "stdout_sha256": _digest(completed.stdout),
                "stderr_sha256": _digest(completed.stderr),
            },
        }
    try:
        row = json.loads(completed.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        return {
            "phase": phase,
            "cohort": cohort["id"],
            "task": task,
            "fixture_failure": {
                "type": type(exc).__name__,
                "stdout_sha256": _digest(completed.stdout),
                "stderr_sha256": _digest(completed.stderr),
            },
        }
    row["cohort"] = cohort["id"]
    return row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--python-executable", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    _verify_seals()
    output = Path(args.output).resolve()
    abort = output.parent / "ABORTED.json"
    inflight = output.parent / "INFLIGHT.json"
    if output.exists() or abort.exists() or inflight.exists():
        raise SystemExit("V6 label already used or unresolved; replacement forbidden")
    rows: list[dict] = []

    def execute(phase: str, cohort: dict, task: str) -> bool:
        _atomic_json(
            inflight,
            {"phase": phase, "cohort": cohort["id"], "task": task},
        )
        row = _run_slot(args, phase=phase, cohort=cohort, task=task)
        rows.append(row)
        _write_rows(output, rows)
        inflight.unlink()
        if row.get("fixture_failure"):
            _atomic_json(abort, row)
            return False
        return True

    for task in TASK_IDS:
        if not execute("gate", GATE_COHORT, task):
            print(json.dumps({"expanded": False, "reason": "retained fixture failure"}))
            return 0
    if not gate_passes(rows):
        print(json.dumps({"expanded": False, "reason": "B gate did not pass"}))
        return 0
    for cohort in (GATE_COHORT, *CONFIRMATION_COHORTS):
        for task in TASK_IDS:
            if not execute("comparison", cohort, task):
                print(
                    json.dumps({"expanded": True, "reason": "retained fixture failure"})
                )
                return 0
    print(json.dumps({"expanded": True, "observation_count": len(rows)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
