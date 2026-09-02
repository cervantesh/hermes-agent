"""Resume-safe V2 pilot/confirmation runner."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

from .analysis_v2 import final_verdict_v2, pilot_expansion_gate_v2
from .protocol_v2 import (
    CONFIRMATION_EXECUTION_378,
    EXPANSION_EXECUTION_377,
    MODEL,
    PILOT_EXECUTION_377,
    PROVIDER,
    TARGET_REVISION,
    validate_schedule,
)
from .provenance_v2 import source_manifest_digest_v2, source_manifest_v2


EVAL_DIR = Path(__file__).resolve().parent
SEAL = EVAL_DIR / "PROTOCOL_SEAL_V2.json"


def verify_seal_v2() -> dict[str, Any]:
    seal = json.loads(SEAL.read_text(encoding="utf-8"))
    if seal["target_revision"] != TARGET_REVISION:
        raise ValueError("V2 seal and runtime target differ")
    for name, expected in seal["files"].items():
        actual = hashlib.sha256((EVAL_DIR / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"sealed V2 file changed: {name}")
    validate_schedule()
    return seal


def _load(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def _run_fixture(args, task: str, seed: int) -> dict[str, Any]:
    command = [
        sys.executable,
        "-m",
        "evals.shared_context_research.fixture_worker_v2",
        "--repo-root",
        str(Path(args.repo_root).resolve()),
        "--python-executable",
        str(Path(args.python_executable).resolve()),
        "--task",
        task,
        "--schedule-seed",
        str(seed),
        "--provider",
        args.provider,
        "--model",
        args.model,
    ]
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    attempts = 0
    while True:
        attempts += 1
        run = subprocess.run(
            command,
            cwd=EVAL_DIR.parents[1],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=3600,
        )
        lines = [line for line in run.stdout.splitlines() if line.strip()]
        record = json.loads(lines[-1]) if lines and lines[-1].startswith("{") else None
        if run.returncode == 2 and attempts == 1:
            continue
        if run.returncode:
            detail = record or {
                "stdout": run.stdout[-4000:],
                "stderr": run.stderr[-4000:],
            }
            raise RuntimeError(f"V2 fixture failed {task}@{seed}: {detail}")
        if record is None:
            raise RuntimeError(f"V2 fixture emitted no JSON: {run.stderr[-4000:]}")
        record["attempts"] = attempts
        return record


def _append_phase(
    args,
    output: Path,
    records: list[dict[str, Any]],
    tasks: tuple[str, ...],
    seed: int,
) -> None:
    completed = {(row["task"], int(row["schedule_seed"])) for row in records}
    protocol_hash = verify_seal_v2()["files"]["PROTOCOL_FREEZE_V2.md"]
    with output.open("a", encoding="utf-8") as sink:
        for task in tasks:
            key = (task, seed)
            if key in completed:
                print(f"[{seed}] {task}: already recorded", flush=True)
                continue
            if source_manifest_v2(EVAL_DIR) != args.source_manifest:
                raise RuntimeError("decision-critical source changed during V2 run")
            record = _run_fixture(args, task, seed)
            record.update({
                "label": args.label,
                "provider": args.provider,
                "model": args.model,
                "protocol_sha256": protocol_hash,
                "source_manifest": args.source_manifest,
                "source_manifest_sha256": args.source_manifest_sha256,
            })
            sink.write(json.dumps(record, ensure_ascii=False) + "\n")
            sink.flush()
            records.append(record)
            completed.add(key)
            summary = ", ".join(
                f"{arm}:ok={value['ok']}/f={value['handoff_fidelity']}"
                for arm, value in record.get("arms", {}).items()
            )
            print(f"[{seed}] {task}: {summary}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--python-executable", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--provider", default=PROVIDER)
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--auto-expand", action="store_true")
    args = parser.parse_args()
    verify_seal_v2()
    args.source_manifest = source_manifest_v2(EVAL_DIR)
    args.source_manifest_sha256 = source_manifest_digest_v2(args.source_manifest)
    output = EVAL_DIR / "results-private" / args.label / "raw-v2.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    records = _load(output)
    _append_phase(args, output, records, PILOT_EXECUTION_377, 377)
    gate = pilot_expansion_gate_v2(records)
    print(json.dumps({"pilot_gate": gate}, sort_keys=True), flush=True)
    expanded = False
    if args.auto_expand and gate.get("expand"):
        _append_phase(args, output, records, EXPANSION_EXECUTION_377, 377)
        _append_phase(args, output, records, CONFIRMATION_EXECUTION_378, 378)
        expanded = True
    decision = final_verdict_v2(records, expanded=expanded)
    print(json.dumps({"decision": decision, "raw": str(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
