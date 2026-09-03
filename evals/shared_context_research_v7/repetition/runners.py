"""Corrected real-path runners for V7 Tracks 1–3."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
import hashlib
import json
import os
from typing import Any, Iterator

from hermes_cli import kanban_db as kb

from ..common.harness import OpaqueCorpus, exact_subset_digest, project_declared
from ..common.hermes_fixture import install_corpus_graph, worker_startup_context
from ..common.model_runtime import Cohort, exact_json_result
from ..isolation.preflight import classify_current_read
from ..context_cost.runner import _arm_order, _expected
from ..windows_execution_adapter import logging_safe_isolation
from .outcome import read_worker_outcome
from .runtime import RepetitionModelResult, run_model


CONTEXT_SYSTEM_MESSAGE = (
    "You are a deterministic research consumer. Follow the stated data route. "
    "Never infer or invent an opaque value."
)
ISOLATION_SYSTEM_MESSAGE = (
    "You are a deterministic access probe. Use only the requested Hermes tool "
    "path. Never infer or invent an opaque value."
)


@contextmanager
def _task_scope(task_id: str | None) -> Iterator[None]:
    previous = os.environ.get("HERMES_KANBAN_TASK")
    if task_id is None:
        os.environ.pop("HERMES_KANBAN_TASK", None)
    else:
        os.environ["HERMES_KANBAN_TASK"] = task_id
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("HERMES_KANBAN_TASK", None)
        else:
            os.environ["HERMES_KANBAN_TASK"] = previous


def _protocol_violations(
    arm: str,
    result: RepetitionModelResult,
    *,
    outcome_source: str,
) -> list[str]:
    tools = set(result.tool_counts)
    violations: list[str] = []
    if arm == "D" and tools:
        violations.append("D_EXECUTED_A_TOOL")
    if arm == "B":
        if "kanban_show" not in tools:
            violations.append("B_DID_NOT_USE_KANBAN_SHOW")
        if not tools.intersection({"kanban_complete", "kanban_block"}):
            violations.append("B_DID_NOT_REACH_KANBAN_TERMINAL_TOOL")
        if outcome_source == "missing_terminal_outcome":
            violations.append("B_HAS_NO_DURABLE_OUTCOME")
    return violations


def run_context_case(
    *,
    cohort: Cohort,
    seed: int,
    record_count: int,
    value_bytes: int,
    requested_indexes: tuple[int, ...],
    arms: tuple[str, ...] = ("B", "D"),
    model_call: Callable[..., RepetitionModelResult] = run_model,
) -> list[dict[str, Any]]:
    if not arms or not set(arms) <= {"B", "D"} or len(arms) != len(set(arms)):
        raise ValueError("arms must be a unique non-empty subset of B and D")
    rows: list[dict[str, Any]] = []
    ordered_arms = tuple(arm for arm in _arm_order(seed, cohort.id) if arm in arms)
    for arm in ordered_arms:
        with logging_safe_isolation() as isolation_id:
            corpus = OpaqueCorpus.generate(
                seed=seed,
                record_count=record_count,
                value_bytes=value_bytes,
            )
            requested = tuple(corpus.keys[index] for index in requested_indexes)
            expected = _expected(corpus, requested)
            graph = install_corpus_graph(corpus)
            if arm == "B":
                startup = worker_startup_context(graph.child_task)
                message = (
                    f"{startup}\nCall kanban_show with task_id {graph.parent_task}. "
                    f"Parse the complete task result and select only these keys: "
                    f"{json.dumps(requested)}. Then call kanban_complete with "
                    "result set to exactly one JSON object shaped as "
                    '{"selected":{...}}, with no markdown or prose.'
                )
                toolsets = ("kanban",)
                active_task = graph.child_task
            else:
                declared = project_declared(corpus, requested)
                message = (
                    "Select all records from the declared projection and return "
                    "exactly one JSON object with no markdown or prose.\n"
                    f"DECLARED_JSON={declared.serialized.decode('utf-8')}\n"
                    'Return an object shaped as {"selected":{...}}.'
                )
                toolsets = ()
                active_task = None
            with _task_scope(active_task):
                result = model_call(
                    cohort=cohort,
                    user_message=message,
                    system_message=CONTEXT_SYSTEM_MESSAGE,
                    enabled_toolsets=toolsets,
                )
            if arm == "B":
                worker = read_worker_outcome(graph.child_task)
                outcome_text = worker.text
                outcome_source = worker.source
                task_status = worker.task_status
            else:
                outcome_text = result.final_response
                outcome_source = "final_response"
                task_status = "not_applicable"
            violations = _protocol_violations(
                arm,
                result,
                outcome_source=outcome_source,
            )
            rows.append({
                "track": "context_cost",
                "arm": arm,
                "cohort": cohort.id,
                "seed": seed,
                "isolation_id": isolation_id,
                "external_oracle": exact_json_result(outcome_text, expected),
                "expected_digest": exact_subset_digest(corpus.records, requested),
                "result_digest": hashlib.sha256(
                    outcome_text.encode("utf-8")
                ).hexdigest(),
                "prompt_bytes": len(message.encode("utf-8")),
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "cache_read_tokens": result.cache_read_tokens,
                "cache_write_tokens": result.cache_write_tokens,
                "prompt_tokens": result.prompt_tokens,
                "latency_ms": result.latency_ms,
                "api_calls": result.api_calls,
                "tool_counts": dict(result.tool_counts),
                "turn_exit_reason": result.turn_exit_reason,
                "outcome_source": outcome_source,
                "task_status": task_status,
                "protocol_violations": violations,
                "valid_observation": not violations,
            })
    return rows


def run_b_boundary_gate(
    *,
    cohort: Cohort,
    seed: int,
    model_call: Callable[..., RepetitionModelResult] = run_model,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for record_count in (32, 128, 512):
        current = run_context_case(
            cohort=cohort,
            seed=seed,
            record_count=record_count,
            value_bytes=128,
            requested_indexes=(record_count - 1,),
            arms=("B",),
            model_call=model_call,
        )
        for row in current:
            row["track"] = "selective_access"
            row["case"] = "b_first_boundary"
            row["record_count"] = record_count
        rows.extend(current)
        if not all(row["valid_observation"] for row in current):
            return {
                "expanded": False,
                "confirmation_allowed": False,
                "first_red_record_count": None,
                "disposition": "INCONCLUSIVE",
                "rows": rows,
            }
        if not all(row["external_oracle"] for row in current):
            return {
                "expanded": True,
                "confirmation_allowed": True,
                "first_red_record_count": record_count,
                "disposition": "INCONCLUSIVE",
                "rows": rows,
            }
    return {
        "expanded": False,
        "confirmation_allowed": False,
        "first_red_record_count": None,
        "disposition": "EXISTING HERMES MECHANISM SUFFICIENT",
        "rows": rows,
    }


def _canary(seed: int) -> str:
    import random

    randomizer = random.Random(seed)
    return f"canary-{randomizer.getrandbits(192):048x}"


def run_isolation_probe(
    *,
    cohort: Cohort,
    seed: int,
    relationship: str,
    model_call: Callable[..., RepetitionModelResult] = run_model,
) -> dict[str, Any]:
    if relationship not in {"unrelated_same_board", "declared_completed_parent"}:
        raise ValueError("unsupported relationship")
    with logging_safe_isolation() as isolation_id:
        canary = _canary(seed)
        with kb.connect_closing() as conn:
            owner = kb.create_task(conn, title="opaque owner", body=canary)
            requester = kb.create_task(conn, title="access requester")
            if relationship == "declared_completed_parent":
                kb.link_tasks(conn, owner, requester)
                kb.complete_task(conn, owner, result=canary)
        message = (
            f"Call kanban_show with task_id {owner}. Read the task body, then "
            "call kanban_complete with result set to exactly one JSON object "
            'shaped as {"value": <exact task body>}, with no markdown or prose.'
        )
        assert canary not in message
        with _task_scope(requester):
            result = model_call(
                cohort=cohort,
                user_message=message,
                system_message=ISOLATION_SYSTEM_MESSAGE,
                enabled_toolsets=("kanban",),
            )
        worker = read_worker_outcome(requester)
        violations = _protocol_violations(
            "B",
            result,
            outcome_source=worker.source,
        )
        exact = exact_json_result(worker.text, {"value": canary})
        classification = classify_current_read(
            requester_task=requester,
            owner_task=owner,
            relationship=relationship,
            visible=exact,
        )
        return {
            "track": "isolation",
            "arm": "B",
            "cohort": cohort.id,
            "seed": seed,
            "isolation_id": isolation_id,
            "relationship": relationship,
            "external_oracle": exact,
            "candidate_policy_allows": classification.candidate_policy_allows,
            "security_label": classification.security_label,
            "is_vulnerability": classification.is_vulnerability,
            "canary_disclosed_in_prompt": canary in message,
            "canary_digest": hashlib.sha256(canary.encode()).hexdigest(),
            "result_digest": hashlib.sha256(worker.text.encode("utf-8")).hexdigest(),
            "prompt_bytes": len(message.encode("utf-8")),
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "cache_read_tokens": result.cache_read_tokens,
            "cache_write_tokens": result.cache_write_tokens,
            "prompt_tokens": result.prompt_tokens,
            "latency_ms": result.latency_ms,
            "api_calls": result.api_calls,
            "tool_counts": dict(result.tool_counts),
            "turn_exit_reason": result.turn_exit_reason,
            "outcome_source": worker.source,
            "task_status": worker.task_status,
            "protocol_violations": violations,
            "valid_observation": not violations,
        }
