"""Scored Track 1 B/D consumer runner; provider execution is separately gated."""

from __future__ import annotations

from collections.abc import Callable
import hashlib
import json
import os
from typing import Any

from ..common.harness import OpaqueCorpus, exact_subset_digest, project_declared
from ..common.hermes_fixture import install_corpus_graph, worker_startup_context
from ..common.model_runtime import Cohort, ModelResult, exact_json_result, run_model
from ..common.preflight_runner import _isolated_hermes_home


SYSTEM_MESSAGE = (
    "You are a deterministic research consumer. Follow the stated data route, "
    "then return exactly one JSON object and no markdown or prose. Never infer "
    "or invent an opaque value."
)


def _expected(corpus: OpaqueCorpus, requested: tuple[str, ...]) -> dict:
    return {"selected": {key: corpus.records[key] for key in requested}}


def _arm_order(seed: int, cohort: str) -> tuple[str, str]:
    digest = hashlib.sha256(f"{seed}:{cohort}".encode()).digest()
    return ("B", "D") if digest[0] % 2 == 0 else ("D", "B")


def run_case(
    *,
    cohort: Cohort,
    seed: int,
    record_count: int,
    value_bytes: int,
    requested_indexes: tuple[int, ...],
    arms: tuple[str, ...] = ("B", "D"),
    model_call: Callable[..., ModelResult] = run_model,
) -> list[dict[str, Any]]:
    if not arms or not set(arms) <= {"B", "D"} or len(arms) != len(set(arms)):
        raise ValueError("arms must be a unique non-empty subset of B and D")
    rows: list[dict[str, Any]] = []
    ordered_arms = tuple(arm for arm in _arm_order(seed, cohort.id) if arm in arms)
    for arm in ordered_arms:
        with _isolated_hermes_home() as isolation_id:
            corpus = OpaqueCorpus.generate(
                seed=seed, record_count=record_count, value_bytes=value_bytes
            )
            requested = tuple(corpus.keys[index] for index in requested_indexes)
            expected = _expected(corpus, requested)
            graph = install_corpus_graph(corpus)
            startup = worker_startup_context(graph.child_task)
            old_task = os.environ.get("HERMES_KANBAN_TASK")
            os.environ["HERMES_KANBAN_TASK"] = graph.child_task
            try:
                if arm == "B":
                    message = (
                        f"{startup}\nCall kanban_show with task_id "
                        f"{graph.parent_task}. Parse task.result and select only "
                        f"these keys: {json.dumps(requested)}.\n"
                        'Return an object shaped as {"selected":{...}}.'
                    )
                    toolsets = ("kanban",)
                else:
                    declared = project_declared(corpus, requested)
                    declared_text = declared.serialized.decode("utf-8")
                    message = (
                        f"Select all records from the declared projection.\n"
                        f"DECLARED_JSON={declared_text}\n"
                        'Return an object shaped as {"selected":{...}}.'
                    )
                    toolsets = ()
                result = model_call(
                    cohort=cohort,
                    user_message=message,
                    system_message=SYSTEM_MESSAGE,
                    enabled_toolsets=toolsets,
                )
            finally:
                if old_task is None:
                    os.environ.pop("HERMES_KANBAN_TASK", None)
                else:
                    os.environ["HERMES_KANBAN_TASK"] = old_task
            rows.append({
                "track": "context_cost",
                "arm": arm,
                "cohort": cohort.id,
                "seed": seed,
                "isolation_id": isolation_id,
                "external_oracle": exact_json_result(result.final_response, expected),
                "expected_digest": exact_subset_digest(corpus.records, requested),
                "result_digest": hashlib.sha256(
                    result.final_response.encode("utf-8")
                ).hexdigest(),
                "prompt_bytes": len(message.encode("utf-8")),
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "cache_read_tokens": result.cache_read_tokens,
                "latency_ms": result.latency_ms,
                "api_calls": result.api_calls,
                "tool_counts": dict(result.tool_counts),
            })
    return rows
