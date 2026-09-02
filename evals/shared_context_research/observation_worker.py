"""Execute one A/B/C observation in a fresh process."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

from .runtime import PROTOCOL_TARGET, RuntimeConfig, run_observation
from .tasks import TASKS_BY_ID


def _target_identity(repo: Path) -> dict[str, object]:
    head = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()
    dirty = bool(
        subprocess.check_output(
            ["git", "-C", str(repo), "status", "--porcelain"], text=True
        ).strip()
    )
    return {"target_head": head, "target_dirty": dirty}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--python-executable", required=True)
    parser.add_argument("--task", required=True, choices=sorted(TASKS_BY_ID))
    parser.add_argument("--arm", required=True, choices=("A", "B", "C"))
    parser.add_argument("--provider", default="claude-code")
    parser.add_argument("--model", default="claude-haiku-4-5")
    args = parser.parse_args()
    repo = Path(args.repo_root).resolve()
    identity = _target_identity(repo)
    if identity["target_head"] != PROTOCOL_TARGET or identity["target_dirty"]:
        raise SystemExit(f"target identity mismatch: {identity}")
    task = TASKS_BY_ID[args.task]
    result = run_observation(
        task,
        args.arm,
        RuntimeConfig(
            repo_root=repo,
            python_executable=Path(args.python_executable).resolve(),
            provider=args.provider,
            model=args.model,
        ),
    )
    result.update(identity)
    print(json.dumps(result, ensure_ascii=False))
    return 2 if result.get("provider_failure") else 0


if __name__ == "__main__":
    raise SystemExit(main())
