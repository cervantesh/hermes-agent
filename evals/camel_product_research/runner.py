"""Resume-safe, randomized runner for the frozen product research."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys

from tasks import TASKS, TASKS_BY_ID


EVAL_DIR = Path(__file__).resolve().parent
WORKER = EVAL_DIR / "worker.py"


def tree_id(repo: Path) -> dict[str, str | bool]:
    head = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()
    diff = subprocess.check_output(["git", "-C", str(repo), "diff", "--binary", "HEAD"])
    untracked = subprocess.check_output(
        ["git", "-C", str(repo), "ls-files", "--others", "--exclude-standard"],
        text=True,
    ).splitlines()
    material = bytearray(diff)
    for relative in sorted(untracked):
        path = repo / relative
        material.extend(relative.encode("utf-8"))
        if path.is_file():
            material.extend(path.read_bytes())
    return {
        "head": head,
        "dirty": bool(material),
        "tree_digest": hashlib.sha256(material).hexdigest() if material else head,
    }


def _load_existing(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _completed(
    records: list[dict],
    *,
    label: str,
    provider: str,
    model: str,
    seed: int,
    identity: dict[str, str | bool],
) -> set[tuple[str, str, int]]:
    expected = {
        "label": label,
        "provider": provider,
        "model": model,
        "schedule_seed": seed,
        **identity,
    }
    completed: set[tuple[str, str, int]] = set()
    for item in records:
        for field, value in expected.items():
            if item.get(field) != value:
                raise ValueError(
                    f"existing result mixes {field}: {item.get(field)!r} != {value!r}"
                )
        key = (str(item["strategy"]), str(item["task"]), int(item["rep"]))
        if key in completed:
            raise ValueError(f"duplicate existing result: {key!r}")
        completed.add(key)
    return completed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--camel-root", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--strategies", default="baseline")
    parser.add_argument("--tasks", default="")
    parser.add_argument("--reps", type=int, default=1)
    parser.add_argument("--seed", type=int, default=375)
    args = parser.parse_args()

    repo = Path(args.repo_root).resolve()
    camel = Path(args.camel_root).resolve()
    tasks = [item for item in args.tasks.split(",") if item] or [
        task.task_id for task in TASKS
    ]
    strategies = [item for item in args.strategies.split(",") if item]
    unknown = sorted(set(tasks) - TASKS_BY_ID.keys())
    if unknown:
        raise SystemExit(f"unknown tasks: {', '.join(unknown)}")
    if not strategies or set(strategies) - {"baseline", "camel"}:
        raise SystemExit("strategies must be baseline and/or camel")

    schedule = [
        (strategy, task, rep)
        for rep in range(1, args.reps + 1)
        for task in tasks
        for strategy in strategies
    ]
    random.Random(args.seed).shuffle(schedule)
    slug = args.model.replace("/", "_").replace("\\", "_")
    output = EVAL_DIR / "results" / args.label / f"{slug}.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    identity = tree_id(repo)
    completed = _completed(
        _load_existing(output),
        label=args.label,
        provider=args.provider,
        model=args.model,
        seed=args.seed,
        identity=identity,
    )
    with output.open("a", encoding="utf-8") as sink:
        for strategy, task_id, rep in schedule:
            key = (strategy, task_id, rep)
            if key in completed:
                print(f"[{strategy} rep{rep}] {task_id}: already recorded")
                continue
            command = [
                sys.executable,
                str(WORKER),
                "--repo-root",
                str(repo),
                "--camel-root",
                str(camel),
                "--task",
                task_id,
                "--strategy",
                strategy,
                "--provider",
                args.provider,
                "--model",
                args.model,
            ]
            env = dict(os.environ)
            env["PYTHONUTF8"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"
            run = subprocess.run(
                command,
                text=True,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                timeout=1800,
            )
            if run.returncode:
                raise SystemExit(
                    f"worker failed for {strategy}/{task_id}:\n"
                    f"STDOUT:\n{run.stdout}\nSTDERR:\n{run.stderr}"
                )
            lines = [line for line in run.stdout.splitlines() if line.strip()]
            result = json.loads(lines[-1])
            result.update({
                "label": args.label,
                "rep": rep,
                "provider": args.provider,
                "model": args.model,
                "schedule_seed": args.seed,
                "repo": str(repo),
                "camel_repo": str(camel),
                **identity,
            })
            sink.write(json.dumps(result, ensure_ascii=False) + "\n")
            sink.flush()
            completed.add(key)
            print(
                f"[{strategy} rep{rep}] {task_id}: ok={result['ok']} "
                f"false_success={result['false_success']} "
                f"calls={result['api_calls']} duration={result['duration_seconds']}s",
                flush=True,
            )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
