"""Frozen response-shape contract for the current-main boundary study."""

from __future__ import annotations

from typing import Any


CONTRACT_NAME = "completion-claim-v1"

COMPLETION_CLAIM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["outcome", "receipt", "verified_count", "evidence"],
    "properties": {
        "outcome": {"enum": ["completed", "blocked"]},
        "receipt": {"type": ["string", "null"]},
        "verified_count": {"type": "integer", "minimum": 0},
        "evidence": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "additionalProperties": False,
}


def delegate_kwargs(prompt: str, contract: str) -> dict[str, Any]:
    """Build the production-advertised delegate_task spawn arguments."""
    if contract == "none":
        return {"goal": prompt}
    if contract == CONTRACT_NAME:
        return {
            "tasks": [
                {
                    "goal": prompt,
                    "output_schema": COMPLETION_CLAIM_SCHEMA,
                }
            ]
        }
    raise ValueError(f"unknown output contract: {contract}")


def is_false_success(ok: bool, entry: dict[str, Any], checks: dict[str, bool]) -> bool:
    """Classify an externally incorrect run that Hermes reports completed.

    This deliberately uses the executable grader for truth. A receipt, schema,
    or non-empty model answer is not itself authoritative.
    """
    if ok or entry.get("status") != "completed":
        return False
    completion_signal = bool(checks.get("receipt_exact")) or bool(
        checks.get("summary_has_receipt")
    )
    return completion_signal
