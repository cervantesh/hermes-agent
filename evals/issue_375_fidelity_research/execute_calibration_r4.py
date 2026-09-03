"""Authorized executor for the efficacy-blind R4 judge calibration."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

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


PROTOCOL_ID = "IP375-JUDGE-CALIBRATION-R4-2026-09-03"
PROTOCOL_SHA256 = "82e3168595ebf6b57acf0256e8e6d14627275a647b4e05b749ec0c68ef778266"
GENERATOR_MODEL = "claude-haiku-4-5-20251001"
FIDELITY_JUDGE_MODEL = "gpt-4-0613"
CONTROL_JUDGE_MODEL = "claude-sonnet-4-5-20250929"
LIMITS = {
    "max_logical_calls": 2700,
    "max_transport_attempts": 8100,
    "max_input_tokens": 6_000_000,
    "max_output_tokens": 3_000_000,
    "max_cost_usd": 20.0,
    "max_wall_clock_seconds": 4 * 60 * 60,
}


class DeadlineExceeded(RuntimeError):
    pass


class FidelityJudgeUnavailable(RuntimeError):
    pass


class DeadlineBackend:
    """Prevent a new provider dispatch after the persistent run deadline."""

    def __init__(
        self,
        backend: Any,
        *,
        deadline_epoch: float,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.backend = backend
        self.deadline_epoch = deadline_epoch
        self.clock = clock
        existing = getattr(backend, "before_attempt", None)

        def before_attempt() -> None:
            self._check()
            if existing is not None:
                existing()

        if hasattr(backend, "before_attempt"):
            backend.before_attempt = before_attempt

    def _check(self) -> None:
        if self.clock() >= self.deadline_epoch:
            raise DeadlineExceeded("R4 wall-clock deadline reached before dispatch")

    @property
    def receipts(self) -> list[dict[str, Any]]:
        return self.backend.receipts

    def complete(self, **kwargs: Any) -> Any:
        self._check()
        return self.backend.complete(**kwargs)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_protocol(root: Path) -> None:
    artifact = root / "JUDGE_CALIBRATION_R4_FREEZE.md"
    seal = json.loads(
        (root / "JUDGE_CALIBRATION_R4_SEAL.json").read_text(encoding="utf-8")
    )
    if (
        seal.get("protocol_id") != PROTOCOL_ID
        or seal.get("sha256") != PROTOCOL_SHA256
        or seal.get("observations_started") is not False
        or _file_sha256(artifact) != PROTOCOL_SHA256
    ):
        raise ValueError("R4 protocol artifact does not match its seal")


def _validate_inputs(*, root: Path, manifest_path: Path, schedule_path: Path) -> str:
    _validate_protocol(root)
    seal_path = root / "frozen_inputs" / "R4_INPUTS_SEAL.json"
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    expected = seal["artifacts"]
    if (
        seal.get("protocol_id") != PROTOCOL_ID
        or seal.get("protocol_sha256") != PROTOCOL_SHA256
        or seal.get("sample_size") != 30
        or seal.get("observations_started") is not False
        or _file_sha256(manifest_path) != expected["R4_MANIFEST.json"]
        or _file_sha256(schedule_path) != expected["R4_SCHEDULE.json"]
        or any(
            _file_sha256(root / "frozen_inputs" / name) != digest
            for name, digest in seal.get("prompt_artifact_sha256", {}).items()
        )
    ):
        raise ValueError(
            "provided manifest or schedule does not match sealed R4 inputs"
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
            "provided manifest or schedule does not match sealed R4 inputs"
        )
    return _file_sha256(seal_path)


def _authorization(
    path: Path, inputs_seal_sha256: str, harness_commit: str
) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError("R4 authorization is absent; refusing provider calls")
    authorization = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "protocol_id": PROTOCOL_ID,
        "protocol_sha256": PROTOCOL_SHA256,
        "inputs_seal_sha256": inputs_seal_sha256,
        "harness_commit": harness_commit,
        "generation_and_extraction_provider": "anthropic",
        "generation_and_extraction_model": GENERATOR_MODEL,
        "fidelity_judge_provider": "openai",
        "fidelity_judge_model": FIDELITY_JUDGE_MODEL,
        "control_judge_provider": "anthropic",
        "control_judge_model": CONTROL_JUDGE_MODEL,
        "limits": LIMITS,
    }
    allowed = {"approved", *expected}
    if set(authorization) != allowed or any(
        authorization.get(key) != value for key, value in expected.items()
    ):
        raise ValueError("run authorization does not match frozen R4")
    if authorization.get("approved") is not True:
        raise ValueError("R4 run authorization is not approved")
    return authorization


def _ensure_output_outside_repo(repo: Path, output_root: Path) -> None:
    repo = repo.resolve()
    output_root = output_root.resolve()
    if output_root == repo or repo in output_root.parents:
        raise ValueError("R4 output root must be outside the repository")


def _bind_run_identity(
    output_root: Path, expected: dict[str, Any], *, now: float | None = None
) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    path = output_root / "R4_RUN_IDENTITY.json"
    if path.exists():
        actual = json.loads(path.read_text(encoding="utf-8"))
        started = actual.get("started_at_epoch")
        derived_deadline = (
            started + LIMITS["max_wall_clock_seconds"]
            if isinstance(started, (int, float))
            else None
        )
        if (
            actual.get("schema_version") != 1
            or actual.get("deadline_epoch") != derived_deadline
            or any(actual.get(key) != value for key, value in expected.items())
        ):
            raise ValueError("output root belongs to a different evidence frame")
        return actual
    if any(output_root.iterdir()):
        raise ValueError("refusing an unbound output root with existing state")
    started = time.time() if now is None else now
    identity = {
        "schema_version": 1,
        **expected,
        "started_at_epoch": started,
        "deadline_epoch": started + LIMITS["max_wall_clock_seconds"],
    }
    _atomic_write(path, identity)
    return identity


def _harness_commit(repo: Path) -> str:
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if status.strip():
        raise RuntimeError("R4 requires a clean committed harness tree")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _budget(path: Path) -> UsageBudget:
    fields = {
        "max_logical_calls",
        "max_transport_attempts",
        "max_input_tokens",
        "max_output_tokens",
        "max_cost_usd",
    }
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

    return UsageBudget(
        **{name: LIMITS[name] for name in fields}, **usage, on_change=save
    )


def _validate_effective_prompts(
    *,
    root: Path,
    dataset: Path,
    manifest: Path,
    camel_repo: Path,
    supplement_tex: Path,
) -> None:
    expected = json.loads(
        (root / "frozen_inputs" / "R4_EFFECTIVE_SYSTEM_PROMPTS.json").read_text(
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
        raise ValueError("effective R4 prompts do not match the sealed artifact")


def _base_preflight_ready(preflight: dict[str, Any]) -> bool:
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
) -> tuple[int, dict[str, Any] | None]:
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
            return attempted, receipt
    return attempted, None


def _run_track(
    *,
    tasks: list[dict[str, str]],
    schedules: dict[str, dict[str, Any]],
    store: CalibrationStore,
    sources: Any,
    judge: Any,
    track: str,
    render_prompt: Callable[..., str] = render_evaluation_prompt,
) -> dict[str, Any]:
    agreements = 0
    for index, task in enumerate(tasks):
        task_id = task["id"]
        forward = list(schedules[task_id]["judge_order"])
        private = store.load_fixture_private(task_id)
        for order, answer_order in (
            ("forward", forward),
            ("reverse", list(reversed(forward))),
        ):
            prompt = render_prompt(
                sources,
                task["specified_task"],
                private["solutions"][answer_order[0]],
                private["solutions"][answer_order[1]],
            )
            receipt = evaluate_judgment(
                store=store,
                task_id=task_id,
                track=track,
                order=order,
                answer_order=answer_order,
                system_prompt=sources.evaluation_system,
                user_prompt=prompt,
                backend=judge,
            )
            if receipt.get("status") != "COMPLETE":
                return receipt
        forward_private = store.load_judgment_private(task_id, track, "forward")
        reverse_private = store.load_judgment_private(task_id, track, "reverse")
        agreements += int(
            forward_private["mapped_outcome"] == reverse_private["mapped_outcome"]
        )
        remaining = len(tasks) - index - 1
        if agreements + remaining < 27:
            return {"status": "REVERSAL_THRESHOLD_UNREACHABLE", "track": track}
    return {"status": "TRACK_COMPLETE", "track": track}


def _track_pass(metrics: dict[str, Any]) -> bool:
    return (
        metrics.get("complete_judgments") == 60
        and metrics.get("invalid_judgments") == 0
        and metrics.get("model_identity_failures") == 0
        and metrics.get("reversal_pairs") == 30
        and metrics.get("reversal_agreements", 0) >= 27
    )


def _control_status(metrics: dict[str, Any], *, ran: bool) -> str:
    if not ran:
        return "NOT_RUN"
    return "PASS" if _track_pass(metrics) else "NONCONFORMANT"


def _run_sequential_tracks(
    *,
    tasks: list[dict[str, str]],
    schedules: dict[str, dict[str, Any]],
    store: CalibrationStore,
    sources: Any,
    fidelity_judge: Any,
    control_judge: Any,
) -> tuple[dict[str, Any], bool, dict[str, Any] | None]:
    fidelity_terminal = _run_track(
        tasks=tasks,
        schedules=schedules,
        store=store,
        sources=sources,
        judge=fidelity_judge,
        track="fidelity",
    )
    fidelity_metrics = summarize_calibration(
        store=store,
        task_ids=[task["id"] for task in tasks],
        tracks=["fidelity"],
    )["tracks"]["fidelity"]
    fidelity_pass = fidelity_terminal["status"] == "TRACK_COMPLETE" and _track_pass(
        fidelity_metrics
    )
    control_terminal = None
    if fidelity_pass:
        control_terminal = _run_track(
            tasks=tasks,
            schedules=schedules,
            store=store,
            sources=sources,
            judge=control_judge,
            track="control",
        )
    return fidelity_terminal, fidelity_pass, control_terminal


def _primary_disposition(
    metrics: dict[str, Any], terminal: dict[str, Any] | None
) -> str:
    if terminal and terminal.get("cause_type") in {
        "ModelIdentityError",
        "FidelityJudgeUnavailable",
    }:
        return "INCONCLUSIVE_FIDELITY_JUDGE_UNAVAILABLE"
    if terminal and terminal.get("status") in {
        "QUARANTINED_JUDGE_OUTPUT_FORMAT",
        "QUARANTINED_JUDGE_SCORE_RANGE",
        "REVERSAL_THRESHOLD_UNREACHABLE",
    }:
        return "INCONCLUSIVE_JUDGE_PROTOCOL_NONCONFORMANCE"
    if terminal:
        return "INCONCLUSIVE_HARNESS_OR_INFRASTRUCTURE"
    return (
        "FIDELITY_JUDGE_CONFORMANCE_PASS"
        if _track_pass(metrics)
        else "INCONCLUSIVE_JUDGE_PROTOCOL_NONCONFORMANCE"
    )


def _verify_model_metadata(
    openai_client: Any,
    anthropic_client: Any,
    *,
    deadline_epoch: float,
    clock: Callable[[], float] = time.time,
) -> None:
    if clock() >= deadline_epoch:
        raise DeadlineExceeded("R4 wall-clock deadline reached before metadata check")
    try:
        openai_model = openai_client.models.retrieve(FIDELITY_JUDGE_MODEL)
    except Exception as error:
        raise FidelityJudgeUnavailable(
            "fidelity judge snapshot metadata is unavailable"
        ) from error
    if getattr(openai_model, "id", None) != FIDELITY_JUDGE_MODEL:
        raise FidelityJudgeUnavailable("fidelity judge snapshot is unavailable")
    for model in (GENERATOR_MODEL, CONTROL_JUDGE_MODEL):
        if clock() >= deadline_epoch:
            raise DeadlineExceeded(
                "R4 wall-clock deadline reached before metadata check"
            )
        anthropic_model = anthropic_client.models.retrieve(model_id=model)
        if getattr(anthropic_model, "id", None) != model:
            raise RuntimeError(f"Anthropic snapshot is unavailable: {model}")


def _usage_is_lower_bound(terminal: dict[str, Any] | None) -> bool:
    if not terminal:
        return False
    if terminal.get("status") == "QUARANTINED_UNKNOWN_PROVIDER_OUTCOME":
        return True
    if any(
        receipt.get("usage_unknown") is True
        for receipt in terminal.get("transport_receipts", [])
    ):
        return True
    transport_failure_types = {
        "APIConnectionError",
        "APITimeoutError",
        "ConnectionError",
        "TimeoutError",
    }
    if terminal.get("cause_type") in transport_failure_types:
        return True
    known = {
        "BudgetExceeded",
        "DeadlineExceeded",
        "FidelityJudgeUnavailable",
        "ModelIdentityError",
        "ProviderContentError",
    }
    return (
        terminal.get("status")
        in {
            "QUARANTINED_FIXTURE_FAILURE",
            "QUARANTINED_JUDGE_TRANSPORT_OR_IDENTITY",
        }
        and terminal.get("cause_type") not in known
        and not terminal.get("transport_receipts")
    )


def _write_summary(
    *,
    path: Path,
    store: CalibrationStore,
    task_ids: list[str],
    ready: int,
    budget: UsageBudget,
    primary_terminal: dict[str, Any] | None,
    control_ran: bool,
    lower_bound: bool = False,
    transport_backends: tuple[Any, ...] = (),
) -> dict[str, Any]:
    summary = summarize_calibration(
        store=store, task_ids=task_ids, tracks=["fidelity", "control"]
    )
    summary["protocol_id"] = PROTOCOL_ID
    summary["judge_ready_fixtures"] = ready
    summary["usage"] = budget.snapshot()
    summary["usage_is_lower_bound"] = (
        lower_bound
        or store.has_durable_unknown_usage(task_ids)
        or any(
            receipt.get("usage_unknown") is True
            for backend in transport_backends
            for receipt in getattr(backend, "receipts", [])
        )
    )
    summary["disposition"] = _primary_disposition(
        summary["tracks"]["fidelity"], primary_terminal
    )
    summary["control_status"] = _control_status(
        summary["tracks"]["control"], ran=control_ran
    )
    _atomic_write(path, summary)
    return summary


def execute(args: argparse.Namespace) -> dict[str, Any]:
    root = args.repo / "evals" / "issue_375_fidelity_research"
    _ensure_output_outside_repo(args.repo, args.output_root)
    harness_commit = _harness_commit(args.repo)
    inputs_seal_sha256 = _validate_inputs(
        root=root, manifest_path=args.manifest, schedule_path=args.schedule
    )
    authorization = _authorization(
        root / "R4_RUN_AUTHORIZATION.json", inputs_seal_sha256, harness_commit
    )
    input_seal = json.loads(
        (root / "frozen_inputs" / "R4_INPUTS_SEAL.json").read_text(encoding="utf-8")
    )
    identity = _bind_run_identity(
        args.output_root,
        {
            "protocol_id": PROTOCOL_ID,
            "protocol_sha256": PROTOCOL_SHA256,
            "inputs_seal_sha256": inputs_seal_sha256,
            "harness_commit": harness_commit,
            "source_digests": {
                "dataset": input_seal["dataset_sha256"],
                "paper_pdf": "926c73c2ae9f9abc7612ab58373e428476f4de55db78646ed59de09810db7777",
                "paper_source": "232dc85336d51948808effa9590087b47ccdb7e4baa364b39120743da050faf2",
                **input_seal["prompt_artifact_sha256"],
            },
            "providers": {
                "generation_and_extraction": authorization[
                    "generation_and_extraction_provider"
                ],
                "fidelity_judge": authorization["fidelity_judge_provider"],
                "control_judge": authorization["control_judge_provider"],
            },
            "models": {
                "generation_and_extraction": GENERATOR_MODEL,
                "fidelity_judge": FIDELITY_JUDGE_MODEL,
                "control_judge": CONTROL_JUDGE_MODEL,
            },
            "limits": LIMITS,
        },
    )
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
    if not _base_preflight_ready(preflight):
        raise RuntimeError("preflight is not READY; refusing provider calls")
    if _file_sha256(args.dataset) != input_seal["dataset_sha256"]:
        raise ValueError("dataset bytes do not match the sealed R4 source")
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

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    tasks = resolve_manifest(args.dataset, manifest)
    task_ids = [task["id"] for task in tasks]
    schedules = {
        row["task_id"]: row
        for row in json.loads(args.schedule.read_text(encoding="utf-8"))
    }
    sources = load_prompt_sources(
        args.camel_repo,
        "c402032a7f7cd27e196356fbcf413c521a8cb4ca",
        args.supplement_tex,
    )
    budget = _budget(args.output_root / "R4_BUDGET_STATE.json")
    store = CalibrationStore(args.output_root / "r4")
    try:
        _verify_model_metadata(
            openai_client,
            anthropic_client,
            deadline_epoch=identity["deadline_epoch"],
        )
    except FidelityJudgeUnavailable:
        return _write_summary(
            path=args.output_root / "R4_PUBLIC_SUMMARY.json",
            store=store,
            task_ids=task_ids,
            ready=0,
            budget=budget,
            primary_terminal={
                "status": "MODEL_METADATA_UNAVAILABLE",
                "cause_type": "FidelityJudgeUnavailable",
            },
            control_ran=False,
        )
    except Exception as error:
        return _write_summary(
            path=args.output_root / "R4_PUBLIC_SUMMARY.json",
            store=store,
            task_ids=task_ids,
            ready=0,
            budget=budget,
            primary_terminal={
                "status": "MODEL_METADATA_PREFLIGHT_FAILED",
                "cause_type": type(error).__name__,
            },
            control_ran=False,
        )
    common_anthropic = {
        "client": anthropic_client,
        "budget": budget,
        "max_attempts": 3,
        "retry_waits": (2, 4),
    }
    generator = DeadlineBackend(
        AnthropicBackend(
            **common_anthropic,
            model=GENERATOR_MODEL,
            input_usd_per_million=1,
            output_usd_per_million=5,
            reserve_usd=0.25,
        ),
        deadline_epoch=identity["deadline_epoch"],
    )
    extractor = DeadlineBackend(
        AnthropicBackend(
            **common_anthropic,
            model=GENERATOR_MODEL,
            input_usd_per_million=1,
            output_usd_per_million=5,
            reserve_usd=0.25,
        ),
        deadline_epoch=identity["deadline_epoch"],
    )
    fidelity_judge = DeadlineBackend(
        OpenAIChatBackend(
            client=openai_client,
            model=FIDELITY_JUDGE_MODEL,
            input_usd_per_million=30,
            output_usd_per_million=60,
            budget=budget,
            max_attempts=3,
            retry_waits=(2, 4),
            reserve_usd=0.50,
        ),
        deadline_epoch=identity["deadline_epoch"],
    )
    control_judge = DeadlineBackend(
        AnthropicBackend(
            **common_anthropic,
            model=CONTROL_JUDGE_MODEL,
            input_usd_per_million=3,
            output_usd_per_million=15,
            reserve_usd=0.65,
        ),
        deadline_epoch=identity["deadline_epoch"],
    )
    interrupted_fixtures = store.recover_interrupted_fixtures()
    interrupted_judgments = store.recover_interrupted_judgments()
    interrupted_fidelity = any(
        receipt.get("track") == "fidelity" for receipt in interrupted_judgments
    )
    interrupted_control = bool(interrupted_judgments) and not interrupted_fidelity
    if interrupted_fixtures or interrupted_fidelity or interrupted_control:
        return _write_summary(
            path=args.output_root / "R4_PUBLIC_SUMMARY.json",
            store=store,
            task_ids=task_ids,
            ready=sum(
                store.has_fixture(task_id)
                and store.load_fixture_public(task_id).get("status") == "JUDGE_READY"
                for task_id in task_ids
            ),
            budget=budget,
            primary_terminal=(
                {"status": "QUARANTINED_UNKNOWN_PROVIDER_OUTCOME"}
                if interrupted_fixtures or interrupted_fidelity
                else None
            ),
            control_ran=interrupted_control,
            lower_bound=True,
            transport_backends=(generator, extractor, fidelity_judge, control_judge),
        )

    _attempted, fixture_terminal = _prepare_fixtures_until_failure(
        tasks=tasks,
        schedules=schedules,
        store=store,
        sources=sources,
        generator=generator,
        extractor=extractor,
    )
    ready = sum(
        store.has_fixture(task_id)
        and store.load_fixture_public(task_id).get("status") == "JUDGE_READY"
        for task_id in task_ids
    )
    if fixture_terminal or ready != 30:
        return _write_summary(
            path=args.output_root / "R4_PUBLIC_SUMMARY.json",
            store=store,
            task_ids=task_ids,
            ready=ready,
            budget=budget,
            primary_terminal=fixture_terminal or {"status": "FIXTURE_GATE_FAILED"},
            control_ran=False,
            lower_bound=_usage_is_lower_bound(fixture_terminal),
            transport_backends=(generator, extractor, fidelity_judge, control_judge),
        )

    fidelity_terminal, fidelity_pass, control_terminal = _run_sequential_tracks(
        tasks=tasks,
        schedules=schedules,
        store=store,
        sources=sources,
        fidelity_judge=fidelity_judge,
        control_judge=control_judge,
    )
    return _write_summary(
        path=args.output_root / "R4_PUBLIC_SUMMARY.json",
        store=store,
        task_ids=task_ids,
        ready=ready,
        budget=budget,
        primary_terminal=(
            None
            if fidelity_terminal["status"] == "TRACK_COMPLETE"
            else fidelity_terminal
        ),
        control_ran=fidelity_pass,
        lower_bound=(
            _usage_is_lower_bound(
                None
                if fidelity_terminal["status"] == "TRACK_COMPLETE"
                else fidelity_terminal
            )
            or _usage_is_lower_bound(control_terminal)
        ),
        transport_backends=(generator, extractor, fidelity_judge, control_judge),
    )


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
