"""Resume-safe runner for the sealed shared-context experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
from typing import Any

from .analysis import final_verdict, pilot_expansion_gate
from .runtime import PROTOCOL_TARGET
from .tasks import TASKS, TASKS_BY_ID


EVAL_DIR = Path(__file__).resolve().parent
SEAL = EVAL_DIR / "PROTOCOL_SEAL.json"


def verify_seal() -> dict[str, Any]:
    seal = json.loads(SEAL.read_text(encoding="utf-8"))
    if seal["target_revision"] != PROTOCOL_TARGET:
        raise ValueError("protocol target and runtime target differ")
    for name, expected in seal["files"].items():
        actual = hashlib.sha256((EVAL_DIR / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"sealed file changed: {name}")
    return seal


def _load(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def _schedule(tasks: list[str], seed: int) -> list[tuple[str, str]]:
    values = [(task, arm) for task in tasks for arm in ("A", "B", "C")]
    random.Random(seed).shuffle(values)
    return values


def _run_one(args, task: str, arm: str) -> dict[str, Any]:
    command = [
        sys.executable,
        "-m",
        "evals.shared_context_research.observation_worker",
        "--repo-root",
        str(Path(args.repo_root).resolve()),
        "--python-executable",
        str(Path(args.python_executable).resolve()),
        "--task",
        task,
        "--arm",
        arm,
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
            timeout=1800,
        )
        lines = [line for line in run.stdout.splitlines() if line.strip()]
        record = json.loads(lines[-1]) if lines and lines[-1].startswith("{") else None
        if run.returncode == 2 and attempts == 1:
            continue
        if run.returncode:
            detail = record or {
                "stdout": run.stdout[-2000:],
                "stderr": run.stderr[-2000:],
            }
            raise RuntimeError(f"observation failed {task}/{arm}: {detail}")
        if record is None:
            raise RuntimeError(f"observation emitted no JSON: {run.stderr[-2000:]}")
        record["attempts"] = attempts
        return record


def _append_phase(
    args, output: Path, records: list[dict], tasks: list[str], seed: int
) -> None:
    completed = {
        (row["task"], row["arm"], int(row["schedule_seed"])) for row in records
    }
    with output.open("a", encoding="utf-8") as sink:
        for task, arm in _schedule(tasks, seed):
            key = (task, arm, seed)
            if key in completed:
                print(f"[{seed}] {task}/{arm}: already recorded", flush=True)
                continue
            record = _run_one(args, task, arm)
            record.update({
                "label": args.label,
                "schedule_seed": seed,
                "provider": args.provider,
                "model": args.model,
                "protocol_sha256": verify_seal()["files"]["PROTOCOL_FREEZE.md"],
            })
            sink.write(json.dumps(record, ensure_ascii=False) + "\n")
            sink.flush()
            records.append(record)
            completed.add(key)
            print(
                f"[{seed}] {task}/{arm}: ok={record['ok']} "
                f"fidelity={record['handoff_fidelity']} tokens={record['total_tokens']} "
                f"duration={record['duration_seconds']}s",
                flush=True,
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--python-executable", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--provider", default="claude-code")
    parser.add_argument("--model", default="claude-haiku-4-5")
    parser.add_argument("--auto-expand", action="store_true")
    args = parser.parse_args()
    verify_seal()
    output = EVAL_DIR / "results-private" / args.label / "raw.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    records = _load(output)
    pilot = [task.task_id for task in TASKS if not task.expansion_only]
    _append_phase(args, output, records, pilot, 377)
    gate = pilot_expansion_gate(records)
    print(json.dumps({"pilot_gate": gate}, sort_keys=True), flush=True)
    expanded = False
    if args.auto_expand and gate.get("expand"):
        expansion = [task.task_id for task in TASKS if task.expansion_only]
        _append_phase(args, output, records, expansion, 377)
        _append_phase(args, output, records, list(TASKS_BY_ID), 378)
        expanded = True
    decision = final_verdict(records, expanded=expanded)
    print(json.dumps({"decision": decision, "raw": str(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
