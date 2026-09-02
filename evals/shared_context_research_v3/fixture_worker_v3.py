"""Execute one V3 fixture in a fresh process."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

from evals.shared_context_research.runtime import RuntimeConfig, _provider_failure
from evals.shared_context_research.tasks import TASKS_BY_ID

from .protocol_v3 import PROVIDER, TARGET_REVISION
from .runtime_v3 import run_fixture_v3


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
    parser.add_argument("--schedule-seed", type=int, choices=(377, 378), required=True)
    parser.add_argument("--provider", default=PROVIDER)
    parser.add_argument("--model", required=True)
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    repo = Path(args.repo_root).resolve()
    identity = _target_identity(repo)
    if identity["target_head"] != TARGET_REVISION or identity["target_dirty"]:
        raise SystemExit(f"target identity mismatch: {identity}")
    try:
        result = run_fixture_v3(
            TASKS_BY_ID[args.task],
            args.schedule_seed,
            RuntimeConfig(
                repo_root=repo,
                python_executable=Path(args.python_executable).resolve(),
                provider=args.provider,
                model=args.model,
            ),
            preflight=args.preflight,
        )
    except Exception as exc:
        marker = _provider_failure(repr(exc))
        if not marker:
            raise
        result = {
            "task": args.task,
            "schedule_seed": args.schedule_seed,
            "preflight": args.preflight,
            "provider_failure": marker,
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "arms": {},
        }
    result.update(identity)
    print(json.dumps(result, ensure_ascii=False))
    return 2 if result.get("provider_failure") else 0


if __name__ == "__main__":
    raise SystemExit(main())
