"""Run a reproducible, interleaved A/B delegation pilot."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import random
import subprocess
import sys

from runner import EVAL_DIR, WORKER, _tree_id
from tasks import TASKS, TASKS_BY_ID


def _task_catalog(suite: str):
    if suite == "completion":
        from completion_contract import COMPLETION_TASKS, COMPLETION_TASKS_BY_ID

        return COMPLETION_TASKS, COMPLETION_TASKS_BY_ID
    if suite == "holdout":
        from anti_bypass_holdout import HOLDOUT_TASKS, HOLDOUT_TASKS_BY_ID

        return HOLDOUT_TASKS, HOLDOUT_TASKS_BY_ID
    if suite == "confirmation":
        from confirmation import CONFIRMATION_TASKS, CONFIRMATION_TASKS_BY_ID

        return CONFIRMATION_TASKS, CONFIRMATION_TASKS_BY_ID
    if suite == "long":
        from long_horizon import LONG_TASKS, LONG_TASKS_BY_ID

        return LONG_TASKS, LONG_TASKS_BY_ID
    return TASKS, TASKS_BY_ID


@dataclass(frozen=True)
class ScheduleItem:
    arm: str
    task_id: str
    rep: int


def build_schedule(task_ids: list[str], reps: int, seed: int) -> list[ScheduleItem]:
    """Randomize pair order while keeping both arms adjacent per observation."""
    rng = random.Random(seed)
    pairs: list[list[ScheduleItem]] = []
    for rep in range(1, reps + 1):
        for task_id in task_ids:
            pair = [
                ScheduleItem("baseline", task_id, rep),
                ScheduleItem("candidate", task_id, rep),
            ]
            rng.shuffle(pair)
            pairs.append(pair)
    rng.shuffle(pairs)
    return [item for pair in pairs for item in pair]


def _completed(path: Path) -> set[tuple[str, int]]:
    if not path.exists():
        return set()
    return {
        (record["task"], record["rep"])
        for record in (
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-root", required=True)
    parser.add_argument("--candidate-root", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument(
        "--suite",
        choices=("short", "long", "confirmation", "holdout", "completion"),
        default="short",
    )
    parser.add_argument("--reps", type=int, default=3)
    parser.add_argument("--seed", type=int, default=375)
    parser.add_argument("--tasks", default="")
    args = parser.parse_args()

    roots = {
        "baseline": Path(args.baseline_root).resolve(),
        "candidate": Path(args.candidate_root).resolve(),
    }
    identities = {arm: _tree_id(root) for arm, root in roots.items()}
    suite_tasks, suite_tasks_by_id = _task_catalog(args.suite)
    task_ids = [item for item in args.tasks.split(",") if item]
    if not task_ids:
        task_ids = [task.task_id for task in suite_tasks]
    unknown = sorted(set(task_ids) - suite_tasks_by_id.keys())
    if unknown:
        raise SystemExit(f"unknown tasks: {', '.join(unknown)}")

    slug = args.model.replace("/", "_").replace("\\", "_")
    paths = {
        arm: EVAL_DIR / "results" / f"{args.label}-{arm}" / f"{slug}.jsonl"
        for arm in roots
    }
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    completed = {arm: _completed(path) for arm, path in paths.items()}

    sinks = {arm: path.open("a", encoding="utf-8") for arm, path in paths.items()}
    try:
        for item in build_schedule(task_ids, args.reps, args.seed):
            key = (item.task_id, item.rep)
            if key in completed[item.arm]:
                print(f"[{item.arm} rep{item.rep}] {item.task_id}: already recorded")
                continue
            print(f"[{item.arm} rep{item.rep}] {item.task_id} ...", flush=True)
            command = [
                sys.executable,
                str(WORKER),
                "--repo-root",
                str(roots[item.arm]),
                "--suite",
                args.suite,
                "--task",
                item.task_id,
                "--provider",
                args.provider,
                "--model",
                args.model,
            ]
            worker_env = dict(os.environ)
            worker_env["PYTHONUTF8"] = "1"
            worker_env["PYTHONIOENCODING"] = "utf-8"
            run = subprocess.run(
                command,
                text=True,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                env=worker_env,
                timeout=900,
            )
            if run.returncode:
                raise SystemExit(
                    f"worker failed for {item.arm}/{item.task_id}:\n"
                    f"STDOUT:\n{run.stdout}\nSTDERR:\n{run.stderr}"
                )
            lines = [line for line in run.stdout.splitlines() if line.strip()]
            result = json.loads(lines[-1])
            result.update(
                {
                    "label": f"{args.label}-{item.arm}",
                    "arm": item.arm,
                    "suite": args.suite,
                    "category": suite_tasks_by_id[item.task_id].category,
                    "rep": item.rep,
                    "provider": args.provider,
                    "model": args.model,
                    "repo": str(roots[item.arm]),
                    "schedule_seed": args.seed,
                    **identities[item.arm],
                }
            )
            sink = sinks[item.arm]
            sink.write(json.dumps(result, ensure_ascii=False) + "\n")
            sink.flush()
            completed[item.arm].add(key)
            print(
                f"[{item.arm} rep{item.rep}] {item.task_id}: "
                f"ok={result['ok']} calls={result['api_calls']} "
                f"duration={result['duration_seconds']}s",
                flush=True,
            )
    finally:
        for sink in sinks.values():
            sink.close()

    for arm, path in paths.items():
        print(f"{arm}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
