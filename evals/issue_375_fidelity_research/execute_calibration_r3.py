"""Authorized executor for the efficacy-blind R3 judge calibration."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .calibration import (
    CalibrationStore,
    evaluate_judgment,
    prepare_and_checkpoint_fixture,
    summarize_calibration,
)
from .execute_lane_r import _atomic_write
from .freeze_effective_prompts import build_artifact as build_effective_prompts
from .manifest import resolve_manifest
from .preflight import run_preflight
from .provider import AnthropicBackend, OpenAIChatBackend, UsageBudget
from .sources import load_prompt_sources, render_evaluation_prompt


PROTOCOL_ID = "IP375-JUDGE-CALIBRATION-R3-2026-09-03"
PROTOCOL_SHA256 = "ab70597ea1515dfb8460fd157578d329c384cb92c99bf1fc5b818cbafb2e18de"
GENERATOR_MODEL = "claude-haiku-4-5-20251001"
FIDELITY_JUDGE_MODEL = "gpt-4-0613"
CONTROL_JUDGE_MODEL = "claude-sonnet-4-5-20250929"
LIMITS = {
    "max_logical_calls": 2700,
    "max_transport_attempts": 8100,
    "max_input_tokens": 6_000_000,
    "max_output_tokens": 3_000_000,
    "max_cost_usd": 20.0,
}


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_inputs(*, root: Path, manifest_path: Path, schedule_path: Path) -> str:
    seal_path = root / "frozen_inputs" / "R3_INPUTS_SEAL.json"
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    expected = seal["artifacts"]
    if (
        seal.get("protocol_id") != PROTOCOL_ID
        or seal.get("protocol_sha256") != PROTOCOL_SHA256
        or seal.get("sample_size") != 30
        or seal.get("observations_started") is not False
        or _file_sha256(manifest_path) != expected["R3_MANIFEST.json"]
        or _file_sha256(schedule_path) != expected["R3_SCHEDULE.json"]
        or any(
            _file_sha256(root / "frozen_inputs" / name) != digest
            for name, digest in seal.get("prompt_artifact_sha256", {}).items()
        )
    ):
        raise ValueError(
            "provided manifest or schedule does not match sealed R3 inputs"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    schedule = json.loads(schedule_path.read_text(encoding="utf-8"))
    manifest_ids = [str(record["id"]) for record in manifest["records"]]
    schedule_ids = [str(record["task_id"]) for record in schedule]
    if (
        len(manifest_ids) != 30
        or set(manifest_ids) != set(schedule_ids)
        or not all(record.get("order_reversal") is True for record in schedule)
    ):
        raise ValueError(
            "provided manifest or schedule does not match sealed R3 inputs"
        )
    return _file_sha256(seal_path)


def _authorization(path: Path, inputs_seal_sha256: str) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError("R3 authorization is absent; refusing provider calls")
    authorization = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "protocol_id": PROTOCOL_ID,
        "protocol_sha256": PROTOCOL_SHA256,
        "inputs_seal_sha256": inputs_seal_sha256,
        "generation_and_extraction_model": GENERATOR_MODEL,
        "fidelity_judge_model": FIDELITY_JUDGE_MODEL,
        "control_judge_model": CONTROL_JUDGE_MODEL,
        "limits": LIMITS,
    }
    if any(authorization.get(key) != value for key, value in expected.items()):
        raise ValueError("run authorization does not match frozen R3")
    if authorization.get("approved") is not True:
        raise ValueError("R3 run authorization is not approved")
    return authorization


def _ensure_output_outside_repo(repo: Path, output_root: Path) -> None:
    repo = repo.resolve()
    output_root = output_root.resolve()
    if output_root == repo or repo in output_root.parents:
        raise ValueError("R3 output root must be outside the repository")


def _budget(path: Path) -> UsageBudget:
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
        _atomic_write(path, {name: snapshot[name] for name in usage})

    return UsageBudget(**LIMITS, **usage, on_change=save)


def _disposition(summary: dict[str, Any]) -> str:
    fidelity = summary["tracks"]["fidelity"]
    if fidelity["model_identity_failures"]:
        return "INCONCLUSIVE_FIDELITY_JUDGE_UNAVAILABLE"
    passed = (
        summary.get("judge_ready_fixtures") == 30
        and fidelity["complete_judgments"] == 60
        and fidelity["invalid_judgments"] == 0
        and fidelity["reversal_pairs"] == 30
        and fidelity["reversal_agreements"] >= 27
    )
    return (
        "FIDELITY_JUDGE_CONFORMANCE_PASS"
        if passed
        else "INCONCLUSIVE_JUDGE_PROTOCOL_NONCONFORMANCE"
    )


def _verify_model_metadata(openai_client: Any, anthropic_client: Any) -> None:
    openai_model = openai_client.models.retrieve(FIDELITY_JUDGE_MODEL)
    if getattr(openai_model, "id", None) != FIDELITY_JUDGE_MODEL:
        raise RuntimeError("fidelity judge snapshot is unavailable")
    for model in (GENERATOR_MODEL, CONTROL_JUDGE_MODEL):
        anthropic_model = anthropic_client.models.retrieve(model_id=model)
        if getattr(anthropic_model, "id", None) != model:
            raise RuntimeError(f"Anthropic snapshot is unavailable: {model}")


def _validate_effective_prompts(
    *,
    root: Path,
    dataset: Path,
    manifest: Path,
    camel_repo: Path,
    supplement_tex: Path,
) -> None:
    expected = json.loads(
        (root / "frozen_inputs" / "R3_EFFECTIVE_SYSTEM_PROMPTS.json").read_text(
            encoding="utf-8"
        )
    )
    actual = build_effective_prompts(
        dataset_path=dataset,
        manifest_path=manifest,
        camel_repo=camel_repo,
        supplement_tex=supplement_tex,
        freeze_id=PROTOCOL_ID,
    )
    if actual != expected:
        raise ValueError("effective R3 prompts do not match the sealed artifact")


def _r3_base_preflight_ready(preflight: dict[str, Any]) -> bool:
    """Reuse the frozen source/runtime checks without requiring stale R2 approval."""
    irrelevant = {
        "explicit_run_authorization_present",
        "authorization_matches_active_protocol",
    }
    return all(
        passed
        for name, passed in preflight["checks"].items()
        if name not in irrelevant and not name.endswith("_present")
    )


def _prepare_fixtures_until_failure(
    *,
    tasks: list[dict[str, str]],
    schedules: dict[str, dict[str, Any]],
    store: CalibrationStore,
    sources: Any,
    generator: Any,
    extractor: Any,
) -> int:
    attempted = 0
    for task in tasks:
        receipt = prepare_and_checkpoint_fixture(
            store=store,
            task=task,
            schedule=schedules[task["id"]],
            sources=sources,
            generator=generator,
            extractor=extractor,
        )
        attempted += 1
        if receipt.get("status") != "JUDGE_READY":
            break
    return attempted


def execute(args: argparse.Namespace) -> dict[str, Any]:
    root = args.repo / "evals" / "issue_375_fidelity_research"
    _ensure_output_outside_repo(args.repo, args.output_root)
    inputs_seal_sha256 = _validate_inputs(
        root=root,
        manifest_path=args.manifest,
        schedule_path=args.schedule,
    )
    _authorization(root / "R3_RUN_AUTHORIZATION.json", inputs_seal_sha256)
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    if not anthropic_key or not openai_key:
        raise RuntimeError("both provider credentials are required; refusing calls")

    preflight = run_preflight(
        repo=args.repo,
        camel_repo=args.camel_repo,
        dataset=args.dataset,
        paper_pdf=args.paper_pdf,
        paper_source=args.paper_source,
        supplement_tex=args.supplement_tex,
    )
    if not _r3_base_preflight_ready(preflight):
        raise RuntimeError("preflight is not READY; refusing provider calls")
    _validate_effective_prompts(
        root=root,
        dataset=args.dataset,
        manifest=args.manifest,
        camel_repo=args.camel_repo,
        supplement_tex=args.supplement_tex,
    )

    import anthropic
    import openai

    anthropic_client = anthropic.Anthropic(
        api_key=anthropic_key, timeout=120.0, max_retries=0
    )
    openai_client = openai.OpenAI(api_key=openai_key, timeout=120.0, max_retries=0)
    _verify_model_metadata(openai_client, anthropic_client)

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    tasks = resolve_manifest(args.dataset, manifest)
    schedules = {
        row["task_id"]: row
        for row in json.loads(args.schedule.read_text(encoding="utf-8"))
    }
    sources = load_prompt_sources(
        args.camel_repo,
        "c402032a7f7cd27e196356fbcf413c521a8cb4ca",
        args.supplement_tex,
    )
    budget = _budget(args.output_root / "R3_BUDGET_STATE.json")
    common_anthropic = {
        "client": anthropic_client,
        "budget": budget,
        "max_attempts": 3,
        "retry_waits": (2, 4),
    }
    generator = AnthropicBackend(
        **common_anthropic,
        model=GENERATOR_MODEL,
        input_usd_per_million=1,
        output_usd_per_million=5,
        reserve_usd=0.25,
    )
    extractor = AnthropicBackend(
        **common_anthropic,
        model=GENERATOR_MODEL,
        input_usd_per_million=1,
        output_usd_per_million=5,
        reserve_usd=0.25,
    )
    judges = {
        "fidelity": OpenAIChatBackend(
            client=openai_client,
            model=FIDELITY_JUDGE_MODEL,
            input_usd_per_million=30,
            output_usd_per_million=60,
            budget=budget,
            max_attempts=3,
            retry_waits=(2, 4),
            reserve_usd=0.50,
        ),
        "control": AnthropicBackend(
            **common_anthropic,
            model=CONTROL_JUDGE_MODEL,
            input_usd_per_million=3,
            output_usd_per_million=15,
            reserve_usd=0.65,
        ),
    }
    store = CalibrationStore(args.output_root / "r3")
    interrupted_fixtures = store.recover_interrupted_fixtures()
    store.recover_interrupted_judgments()
    if interrupted_fixtures:
        raise RuntimeError("interrupted fixture has unknown provider outcome")

    attempted_fixtures = _prepare_fixtures_until_failure(
        tasks=tasks,
        schedules=schedules,
        store=store,
        sources=sources,
        generator=generator,
        extractor=extractor,
    )
    ready = sum(
        store.has_fixture(task["id"])
        and store.load_fixture_public(task["id"]).get("status") == "JUDGE_READY"
        for task in tasks
    )
    if ready != 30:
        summary = {
            "schema_version": 1,
            "protocol_id": PROTOCOL_ID,
            "judge_ready_fixtures": ready,
            "attempted_fixtures": attempted_fixtures,
            "efficacy_observations": 0,
            "eligible_for_pooling": False,
            "disposition": "INCONCLUSIVE_HARNESS_OR_INFRASTRUCTURE",
            "usage": budget.snapshot(),
        }
        _atomic_write(args.output_root / "R3_PUBLIC_SUMMARY.json", summary)
        return summary

    for task in tasks:
        task_id = task["id"]
        schedule = schedules[task_id]
        private = store.load_fixture_private(task_id)
        forward = list(schedule["judge_order"])
        for track, judge in judges.items():
            for order, answer_order in (
                ("forward", forward),
                ("reverse", list(reversed(forward))),
            ):
                prompt = render_evaluation_prompt(
                    sources,
                    task["specified_task"],
                    private["solutions"][answer_order[0]],
                    private["solutions"][answer_order[1]],
                )
                evaluate_judgment(
                    store=store,
                    task_id=task_id,
                    track=track,
                    order=order,
                    answer_order=answer_order,
                    system_prompt=sources.evaluation_system,
                    user_prompt=prompt,
                    backend=judge,
                )

    summary = summarize_calibration(
        store=store,
        task_ids=[task["id"] for task in tasks],
        tracks=["fidelity", "control"],
    )
    summary["judge_ready_fixtures"] = ready
    summary["usage"] = budget.snapshot()
    summary["disposition"] = _disposition(summary)
    _atomic_write(args.output_root / "R3_PUBLIC_SUMMARY.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
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
