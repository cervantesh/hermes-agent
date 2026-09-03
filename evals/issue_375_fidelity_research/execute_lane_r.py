"""Authorized direct-provider executor for Lane R pilot and scored stages."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import anthropic

from .analysis import analyze_wins
from .manifest import resolve_manifest
from .provider import AnthropicBackend, BudgetExceeded, UsageBudget
from .preflight import run_preflight
from .runner import LaneRExecutionError, PairStore, run_lane_r_pair
from .sources import load_prompt_sources


PROTOCOL_ID = "IP375-FIDELITY-EXECUTION-R1-2026-09-03"
PROTOCOL_SHA256 = "78294319621e91540173c2dc19b01eb3b698f70c735cbe7a44ea40b3a5310305"
GENERATOR_MODEL = "claude-haiku-4-5-20251001"
JUDGE_MODEL = "claude-sonnet-4-5-20250929"
STAGE_LIMITS = {
    "pilot": {
        "max_logical_calls": 340,
        "max_transport_attempts": 1020,
        "max_input_tokens": 2_000_000,
        "max_output_tokens": 1_500_000,
        "max_cost_usd": 10.0,
    },
    "scored": {
        "max_logical_calls": 8860,
        "max_transport_attempts": 26580,
        "max_input_tokens": 50_000_000,
        "max_output_tokens": 35_000_000,
        "max_cost_usd": 200.0,
    },
}


def _canonical(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _atomic_write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    with temporary.open("wb") as target:
        target.write(_canonical(value))
        target.flush()
        os.fsync(target.fileno())
    temporary.replace(path)


def _authorization(path: Path, stage: str) -> dict[str, Any]:
    authorization = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "protocol_id": PROTOCOL_ID,
        "protocol_sha256": PROTOCOL_SHA256,
        "stage": stage,
        "generation_and_extraction_model": GENERATOR_MODEL,
        "judge_model": JUDGE_MODEL,
        "limits": STAGE_LIMITS[stage],
    }
    if any(authorization.get(key) != value for key, value in expected.items()):
        raise ValueError("run authorization does not match the frozen stage")
    if authorization.get("approved") is not True:
        raise ValueError("run authorization is not approved")
    return authorization


def _budget(path: Path, stage: str) -> UsageBudget:
    limits = STAGE_LIMITS[stage]
    usage = {
        "logical_calls": 0,
        "transport_attempts": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cost_usd": 0.0,
    }
    if path.exists():
        usage.update(json.loads(path.read_text(encoding="utf-8")))

    def save(snapshot: dict[str, Any]) -> None:
        _atomic_write(
            path,
            {name: snapshot[name] for name in usage},
        )

    return UsageBudget(**limits, **usage, on_change=save)


def _public_summary(
    store: PairStore, task_ids: list[str], budget: UsageBudget, stage: str
):
    receipts = [
        store.load_public(task_id)
        if store.has_public(task_id)
        else {"task_id": task_id, "status": "NOT_RUN"}
        for task_id in task_ids
    ]
    completed = [receipt for receipt in receipts if receipt["status"] == "COMPLETE"]
    quarantined = [receipt for receipt in receipts if receipt["status"] != "COMPLETE"]
    summary: dict[str, Any] = {
        "schema_version": 1,
        "protocol_id": PROTOCOL_ID,
        "stage": stage,
        "status": "COMPLETE" if len(completed) == len(task_ids) else "INCOMPLETE",
        "task_count": len(task_ids),
        "completed_pairs": len(completed),
        "quarantined_pairs": len(quarantined),
        "usage": budget.snapshot(),
    }
    if stage == "pilot":
        summary["efficacy_observations"] = 0
        summary["eligible_for_pooling"] = False
        summary["conformance_pass"] = len(completed) == 4 and not quarantined
        return summary

    wins = {"original": 0, "ablated": 0, "draw": 0}
    for receipt in completed:
        wins[receipt["outcome"]] += 1
    analysis = analyze_wins(
        original_wins=wins["original"],
        ablated_wins=wins["ablated"],
        draws=wins["draw"],
    )
    disagreements = sum(
        bool(receipt.get("reversal") and receipt["reversal"]["disagrees"])
        for receipt in completed
    )
    failures_by_arm = {"original": 0, "ablated": 0}
    for receipt in quarantined:
        arm = receipt.get("arm")
        if arm in failures_by_arm:
            failures_by_arm[arm] += 1
    identity_breach = any(
        receipt.get("cause_type") == "ModelIdentityError" for receipt in quarantined
    )
    differential_failures = abs(
        failures_by_arm["original"] - failures_by_arm["ablated"]
    )
    valid = (
        len(completed) >= 90
        and disagreements <= 4
        and differential_failures <= 5
        and not identity_breach
    )
    summary.update({
        "wins": wins,
        "order_reversal_disagreements": disagreements,
        "failures_by_arm": failures_by_arm,
        "arm_failure_difference": differential_failures,
        "model_identity_breach": identity_breach,
        "validity_gate_pass": valid,
        "analysis": analysis.__dict__,
        "scientific_disposition": (
            analysis.disposition if valid else "INCONCLUSIVE_PROTOCOL_OR_INFRASTRUCTURE"
        ),
    })
    return summary


def execute(args: argparse.Namespace) -> dict[str, Any]:
    root = args.repo / "evals" / "issue_375_fidelity_research"
    _authorization(root / "RUN_AUTHORIZATION.json", args.stage)
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is absent; refusing provider calls")
    preflight = run_preflight(
        repo=args.repo,
        camel_repo=args.camel_repo,
        dataset=args.dataset,
        paper_pdf=args.paper_pdf,
        paper_source=args.paper_source,
        supplement_tex=args.supplement_tex,
    )
    if preflight["status"] != "READY":
        raise RuntimeError("preflight is not READY; refusing provider calls")
    if args.stage == "scored":
        pilot_summary_path = args.output_root / "PILOT_PUBLIC_SUMMARY.json"
        if not pilot_summary_path.is_file():
            raise RuntimeError("scored run requires a completed provider pilot")
        pilot_summary = json.loads(pilot_summary_path.read_text(encoding="utf-8"))
        if pilot_summary.get("conformance_pass") is not True:
            raise RuntimeError("provider pilot did not pass conformance")

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    tasks = resolve_manifest(args.dataset, manifest)
    if args.stage == "pilot":
        tasks = tasks[:4]
    schedules = {
        row["task_id"]: row
        for row in json.loads(args.schedule.read_text(encoding="utf-8"))
    }
    sources = load_prompt_sources(
        args.camel_repo,
        "c402032a7f7cd27e196356fbcf413c521a8cb4ca",
        args.supplement_tex,
    )
    budget = _budget(args.output_root / "BUDGET_STATE.json", args.stage)
    client = anthropic.Anthropic(api_key=api_key, timeout=120.0, max_retries=0)
    common = {
        "client": client,
        "budget": budget,
        "max_attempts": 3,
        "retry_waits": (2, 4),
    }
    generator = AnthropicBackend(
        **common,
        model=GENERATOR_MODEL,
        input_usd_per_million=1,
        output_usd_per_million=5,
        reserve_usd=0.25,
    )
    extractor = AnthropicBackend(
        **common,
        model=GENERATOR_MODEL,
        input_usd_per_million=1,
        output_usd_per_million=5,
        reserve_usd=0.25,
    )
    judge = AnthropicBackend(
        **common,
        model=JUDGE_MODEL,
        input_usd_per_million=3,
        output_usd_per_million=15,
        reserve_usd=0.65,
    )

    store = PairStore(args.output_root / args.stage)
    store.recover_interrupted()
    for task in tasks:
        if not store.begin(task["id"]):
            continue
        try:
            private, public = run_lane_r_pair(
                task=task,
                schedule=schedules[task["id"]],
                sources=sources,
                generator=generator,
                extractor=extractor,
                judge=judge,
            )
        except Exception as error:
            phase = error.phase if isinstance(error, LaneRExecutionError) else "unknown"
            arm = error.arm if isinstance(error, LaneRExecutionError) else None
            cause = error.cause if isinstance(error, LaneRExecutionError) else error
            private = {
                "schema_version": 1,
                "task_id": task["id"],
                "status": "QUARANTINED_RUNTIME_FAILURE",
                "error_type": type(error).__name__,
                "error": str(error),
                "phase": phase,
                "arm": arm,
                "cause_type": type(cause).__name__,
            }
            public = {
                "schema_version": 1,
                "task_id": task["id"],
                "status": "QUARANTINED_RUNTIME_FAILURE",
                "error_type": type(error).__name__,
                "phase": phase,
                "arm": arm,
                "cause_type": type(cause).__name__,
            }
            store.complete(task["id"], private, public)
            if args.stage == "pilot" or isinstance(cause, BudgetExceeded):
                break
        else:
            store.complete(task["id"], private, public)

    summary = _public_summary(store, [task["id"] for task in tasks], budget, args.stage)
    _atomic_write(
        args.output_root / f"{args.stage.upper()}_PUBLIC_SUMMARY.json", summary
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("pilot", "scored"), required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--schedule", type=Path, required=True)
    parser.add_argument("--camel-repo", type=Path, required=True)
    parser.add_argument("--supplement-tex", type=Path, required=True)
    parser.add_argument("--paper-pdf", type=Path, required=True)
    parser.add_argument("--paper-source", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(execute(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
