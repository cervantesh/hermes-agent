"""One-process worker for a V5 B gate or full comparison fixture."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

from evals.shared_context_research.runtime import RuntimeConfig

from .protocol_v5 import PROVIDER, TARGET_REVISION
from .runtime_v5 import run_b_gate_v5, run_comparison_v5
from .tasks_v5 import task_for_seed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("gate", "comparison"), required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--python-executable", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--provider", default=PROVIDER)
    args = parser.parse_args()
    repo = Path(args.repo_root).resolve()
    head = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()
    dirty = bool(
        subprocess.check_output(
            ["git", "-C", str(repo), "status", "--porcelain"], text=True
        ).strip()
    )
    if head != TARGET_REVISION or dirty:
        raise SystemExit(f"target identity mismatch: head={head} dirty={dirty}")
    task = task_for_seed(args.task, args.seed)
    config = RuntimeConfig(
        repo_root=repo,
        python_executable=Path(args.python_executable).resolve(),
        provider=args.provider,
        model=args.model,
    )
    result = (
        run_b_gate_v5(task, config)
        if args.phase == "gate"
        else run_comparison_v5(task, args.seed, config)
    )
    result.update({
        "phase": args.phase,
        "model": args.model,
        "provider": args.provider,
        "target_revision": head,
        "target_dirty": dirty,
    })
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
