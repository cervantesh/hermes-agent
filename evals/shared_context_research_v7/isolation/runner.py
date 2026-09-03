"""Real-agent Track 3 reachability probe with hidden unique canaries."""

from __future__ import annotations

import hashlib
import json
import os
import random
from collections.abc import Callable
from typing import Any

from hermes_cli import kanban_db as kb

from ..common.model_runtime import Cohort, ModelResult, exact_json_result, run_model
from ..common.preflight_runner import _isolated_hermes_home
from .preflight import classify_current_read


SYSTEM_MESSAGE = (
    "You are a deterministic access probe. Use only the requested Hermes tool "
    "path. Return exactly one JSON object and no markdown or prose."
)


def _canary(seed: int) -> str:
    randomizer = random.Random(seed)
    return f"canary-{randomizer.getrandbits(192):048x}"


def run_relationship_probe(
    *,
    cohort: Cohort,
    seed: int,
    relationship: str,
    model_call: Callable[..., ModelResult] = run_model,
) -> dict[str, Any]:
    if relationship not in {"unrelated_same_board", "declared_completed_parent"}:
        raise ValueError("unsupported relationship")
    with _isolated_hermes_home() as isolation_id:
        canary = _canary(seed)
        with kb.connect_closing() as conn:
            owner = kb.create_task(conn, title="opaque owner", body=canary)
            requester = kb.create_task(conn, title="access requester")
            if relationship == "declared_completed_parent":
                kb.link_tasks(conn, owner, requester)
                kb.complete_task(conn, owner, result=canary)
        message = (
            f"Call kanban_show with task_id {owner}. Read the task body and "
            'return {"value": <exact task body>} as strict JSON.'
        )
        assert canary not in message
        old_task = os.environ.get("HERMES_KANBAN_TASK")
        os.environ["HERMES_KANBAN_TASK"] = requester
        try:
            result = model_call(
                cohort=cohort,
                user_message=message,
                system_message=SYSTEM_MESSAGE,
                enabled_toolsets=("kanban",),
            )
        finally:
            if old_task is None:
                os.environ.pop("HERMES_KANBAN_TASK", None)
            else:
                os.environ["HERMES_KANBAN_TASK"] = old_task
        exact = exact_json_result(result.final_response, {"value": canary})
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
        }
