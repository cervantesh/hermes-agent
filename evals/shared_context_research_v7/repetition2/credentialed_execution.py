"""Credentialed entry point for the remaining V7 Tracks 2–3."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ..common.evidence import verify_seal
from ..repetition.credentialed_execution import run_authorized_model
from ..scored_runner import verify_target
from ..windows_execution_adapter import install as install_windows_adapter
from .runners import run_b_boundary_gate, run_context_case, run_isolation_probe
from .study import run_repetition2


ROOT = Path(__file__).resolve().parents[1]


def context_runner(**kwargs: Any) -> list[dict[str, Any]]:
    return run_context_case(**kwargs, model_call=run_authorized_model)


def boundary_runner(**kwargs: Any) -> dict[str, Any]:
    return run_b_boundary_gate(**kwargs, model_call=run_authorized_model)


def isolation_runner(**kwargs: Any) -> dict[str, Any]:
    return run_isolation_probe(**kwargs, model_call=run_authorized_model)


def verify_execution_chain() -> None:
    for seal_name in (
        "PROTOCOL_SEAL.json",
        "AMENDMENT_001_SEAL.json",
        "AMENDMENT_002_SEAL.json",
        "RUN_001_AUDIT_SEAL.json",
        "REPETITION_PROTOCOL_SEAL.json",
        "RUN_002_AUDIT_SEAL.json",
        "REPETITION_002_PROTOCOL_SEAL.json",
    ):
        verify_seal(ROOT, ROOT / seal_name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", required=True)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    verify_target(ROOT.parents[1])
    verify_execution_chain()
    install_windows_adapter()
    receipt = run_repetition2(
        evidence_root=Path(args.evidence_root).resolve(),
        label=args.label,
        context_runner=context_runner,
        boundary_runner=boundary_runner,
        isolation_runner=isolation_runner,
    )
    print(json.dumps({"observation_count": receipt["observation_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
