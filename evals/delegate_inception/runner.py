"""Run a resume-safe delegated-child behavior evaluation against one tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
WORKER = EVAL_DIR / "worker.py"


def _tree_id(repo: Path) -> dict[str, str | bool]:
    head = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()
    diff = subprocess.check_output(
        ["git", "-C", str(repo), "diff", "--binary", "HEAD"],
    )
    untracked = subprocess.check_output(
        ["git", "-C", str(repo), "ls-files", "--others", "--exclude-standard"],
        text=True,
    ).splitlines()
    dirty_material = bytearray(diff)
    for relative in sorted(untracked):
        path = repo / relative
        dirty_material.extend(relative.encode())
        if path.is_file():
            dirty_material.extend(path.read_bytes())
    return {
        "head": head,
        "dirty": bool(dirty_material),
        "tree_digest": hashlib.sha256(dirty_material).hexdigest()
        if dirty_material
        else head,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--reps", type=int, default=3)
    parser.add_argument("--tasks", default="")
    parser.add_argument(
        "--codex-workspace-write",
        action="store_true",
        help=(
            "Allow codex-app-server to write only inside each disposable "
            "evaluation workspace. Network access remains disabled."
        ),
    )
    args = parser.parse_args()

    repo = Path(args.repo_root).resolve()
    selected = [item for item in args.tasks.split(",") if item]
    if not selected:
        from tasks import TASKS

        selected = [task.task_id for task in TASKS]
    identity = _tree_id(repo)
    slug = args.model.replace("/", "_").replace("\\", "_")
    out_dir = EVAL_DIR / "results" / args.label
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{slug}.jsonl"
    completed: set[tuple[str, int]] = set()
    if out_path.exists():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            completed.add((record["task"], record["rep"]))

    with out_path.open("a", encoding="utf-8") as sink:
        for rep in range(1, args.reps + 1):
            for task_id in selected:
                if (task_id, rep) in completed:
                    print(f"[{args.label} rep{rep}] {task_id}: already recorded")
                    continue
                print(f"[{args.label} rep{rep}] {task_id} ...", flush=True)
                command = [
                    sys.executable,
                    str(WORKER),
                    "--repo-root",
                    str(repo),
                    "--task",
                    task_id,
                    "--provider",
                    args.provider,
                    "--model",
                    args.model,
                ]
                if args.codex_workspace_write:
                    command.append("--codex-workspace-write")
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
                        f"worker failed for {task_id}:\nSTDOUT:\n{run.stdout}\n"
                        f"STDERR:\n{run.stderr}"
                    )
                lines = [line for line in run.stdout.splitlines() if line.strip()]
                result = json.loads(lines[-1])
                result.update(
                    {
                        "label": args.label,
                        "rep": rep,
                        "provider": args.provider,
                        "model": args.model,
                        "repo": str(repo),
                        **identity,
                    }
                )
                sink.write(json.dumps(result, ensure_ascii=False) + "\n")
                sink.flush()
                print(
                    f"[{args.label} rep{rep}] {task_id}: ok={result['ok']} "
                    f"calls={result['api_calls']} duration={result['duration_seconds']}s",
                    flush=True,
                )
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
