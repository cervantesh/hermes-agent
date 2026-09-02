"""Execute one V4 fixture and serialize every terminal outcome."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from evals.shared_context_research.runtime import RuntimeConfig, _provider_failure
from evals.shared_context_research.protocol_v2 import arm_order
from evals.shared_context_research.tasks import TASKS_BY_ID
from evals.shared_context_research_v3.runtime_v3 import run_fixture_v3

from .protocol_v4 import PROVIDER, TARGET_REVISION


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


def _failure_record(args: argparse.Namespace, exc: Exception) -> dict[str, object]:
    text = str(exc)
    provider = _provider_failure(repr(exc), text)
    task = TASKS_BY_ID[args.task]
    return {
        "task": args.task,
        "schedule_seed": args.schedule_seed,
        "topology": task.topology,
        "dependent": task.dependent,
        "preflight": args.preflight,
        "order": list(arm_order(args.task, args.schedule_seed)),
        # A terminal exception provides no complete admission receipt. False
        # means "not established", not a claim that the producer was rejected.
        "producer_admitted": False,
        "provider_failure": provider,
        "fixture_failure": None
        if provider
        else {
            "exception_type": type(exc).__name__,
            "failure_phase": "fixture_execution",
            "message_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        },
        "private_exception": text,
        "arms": {},
        "integrity": {},
        "schemas_safe_equal": False,
    }


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
        result = _failure_record(args, exc)
    result.update(identity)
    print(json.dumps(result, ensure_ascii=False))
    if result.get("provider_failure"):
        return 2
    if result.get("fixture_failure"):
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
