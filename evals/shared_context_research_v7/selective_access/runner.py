"""Staged Track 2 boundary search with a B-first stopping rule."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..common.model_runtime import Cohort, ModelResult, run_model
from ..context_cost.runner import run_case


RECORD_COUNTS = (32, 128, 512)
VALUE_BYTES = 128


def run_b_boundary_gate(
    *,
    cohort: Cohort,
    seed: int,
    model_call: Callable[..., ModelResult] = run_model,
    case_runner: Callable[..., list[dict[str, Any]]] = run_case,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for record_count in RECORD_COUNTS:
        current = case_runner(
            cohort=cohort,
            seed=seed,
            record_count=record_count,
            value_bytes=VALUE_BYTES,
            requested_indexes=(record_count - 1,),
            arms=("B",),
            model_call=model_call,
        )
        for row in current:
            row["record_count"] = record_count
        rows.extend(current)
        if not all(row["external_oracle"] for row in current):
            return {
                "expanded": True,
                "first_red_record_count": record_count,
                "disposition": "INCONCLUSIVE",
                "rows": rows,
            }
    return {
        "expanded": False,
        "first_red_record_count": None,
        "disposition": "EXISTING HERMES MECHANISM SUFFICIENT",
        "rows": rows,
    }
