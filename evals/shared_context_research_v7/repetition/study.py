"""Prospective corrected orchestration for the V7 repetition."""

from __future__ import annotations

from collections.abc import Callable
import json
from pathlib import Path
from typing import Any

from ..common.evidence import EvidenceLedger
from ..protocol import (
    COHORTS,
    LATENCY_REDUCTION_GATE,
    TOKEN_REDUCTION_GATE,
    TRACK1_CASES,
    TRACK2_CONFIRMATION_SEEDS,
    TRACK2_GATE_COHORT,
    TRACK2_GATE_SEED,
    TRACK3_RELATIONSHIPS,
    TRACK3_SEED,
)
from .runners import run_b_boundary_gate, run_context_case, run_isolation_probe


def _reduction(baseline: float, candidate: float) -> float:
    if baseline <= 0:
        raise ValueError("baseline metric must be positive")
    return (baseline - candidate) / baseline


def _pair_decision(rows: list[dict[str, Any]], cohort_id: str) -> dict[str, Any]:
    selected = [row for row in rows if row["cohort"] == cohort_id]
    arms = {row["arm"]: row for row in selected}
    if set(arms) != {"B", "D"}:
        return {"passed": False, "reason": "missing arm"}
    if not all(row["valid_observation"] for row in arms.values()):
        return {"passed": False, "reason": "invalid observation"}
    if not all(row["external_oracle"] for row in arms.values()):
        return {"passed": False, "reason": "external success differs"}
    token_reduction = _reduction(arms["B"]["prompt_tokens"], arms["D"]["prompt_tokens"])
    latency_reduction = _reduction(arms["B"]["latency_ms"], arms["D"]["latency_ms"])
    token_path = token_reduction >= TOKEN_REDUCTION_GATE and latency_reduction >= 0
    latency_path = latency_reduction >= LATENCY_REDUCTION_GATE and token_reduction >= 0
    return {
        "passed": token_path or latency_path,
        "reason": "frozen resource gate passed"
        if token_path or latency_path
        else "resource threshold not met",
        "token_reduction": token_reduction,
        "latency_reduction": latency_reduction,
    }


def decide_track1(rows: list[dict[str, Any]]) -> dict[str, Any]:
    subset = [row for row in rows if row.get("case") == "subset"]
    control = [row for row in rows if row.get("case") == "all_records_control"]
    expected = len(COHORTS) * 2
    if len(subset) != expected or len(control) != expected:
        return {"disposition": "INCONCLUSIVE", "reason": "missing frozen observation"}
    if not all(row["valid_observation"] and row["external_oracle"] for row in control):
        return {
            "disposition": "INCONCLUSIVE",
            "reason": "all-records control invalid or not exact",
        }
    if not all(row["valid_observation"] and row["external_oracle"] for row in subset):
        return {
            "disposition": "INCONCLUSIVE",
            "reason": "subset observation invalid or not exact",
        }

    subset_by_cohort = {
        cohort.id: _pair_decision(subset, cohort.id) for cohort in COHORTS
    }
    control_by_cohort = {
        cohort.id: _pair_decision(control, cohort.id) for cohort in COHORTS
    }
    if any(result["passed"] for result in control_by_cohort.values()):
        return {
            "disposition": "INCONCLUSIVE",
            "reason": "all-records control shows the same resource advantage",
            "control_artifact": True,
            "subset_by_cohort": subset_by_cohort,
            "control_by_cohort": control_by_cohort,
        }
    passed = all(result["passed"] for result in subset_by_cohort.values())
    return {
        "disposition": "IMPLEMENTATION OPPORTUNITY"
        if passed
        else "NO DEMONSTRATED INCREMENT",
        "reason": "resource gate repeated in both cohorts"
        if passed
        else "resource gate did not repeat in both cohorts",
        "smaller_footprint_discriminant": "#95561" if passed else None,
        "subset_by_cohort": subset_by_cohort,
        "control_by_cohort": control_by_cohort,
    }


def decide_track3(rows: list[dict[str, Any]]) -> dict[str, Any]:
    positive = [
        row for row in rows if row["relationship"] == "declared_completed_parent"
    ]
    probes = [row for row in rows if row["relationship"] == "unrelated_same_board"]
    if len(positive) != len(COHORTS) or not all(
        row["valid_observation"] and row["external_oracle"] for row in positive
    ):
        return {
            "disposition": "INCONCLUSIVE",
            "reason": "positive control invalid or not exact",
        }
    if len(probes) != len(COHORTS) or not all(
        row["valid_observation"] for row in probes
    ):
        return {
            "disposition": "INCONCLUSIVE",
            "reason": "policy probe invalid or missing",
        }
    visible = [row["external_oracle"] for row in probes]
    if all(visible):
        return {
            "disposition": "INCONCLUSIVE",
            "policy_status": "POLICY_UNADJUDICATED",
            "reason": "unrelated same-board task is reachable in both cohorts",
        }
    if not any(visible):
        return {
            "disposition": "EXISTING HERMES MECHANISM SUFFICIENT",
            "reason": "unrelated same-board task was not recovered in either cohort",
        }
    return {
        "disposition": "INCONCLUSIVE",
        "reason": "policy probes disagree across cohorts",
    }


_PUBLIC_FIELDS = (
    "track",
    "case",
    "arm",
    "cohort",
    "seed",
    "record_count",
    "external_oracle",
    "prompt_bytes",
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
    "prompt_tokens",
    "latency_ms",
    "api_calls",
    "result_digest",
    "tool_counts",
    "turn_exit_reason",
    "outcome_source",
    "task_status",
    "protocol_violations",
    "valid_observation",
    "relationship",
    "candidate_policy_allows",
    "security_label",
    "is_vulnerability",
    "canary_disclosed_in_prompt",
    "canary_digest",
)


def public_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: row[key] for key in _PUBLIC_FIELDS if key in row}


def run_repetition(
    *,
    evidence_root: Path,
    label: str,
    context_runner: Callable[..., list[dict[str, Any]]] = run_context_case,
    boundary_runner: Callable[..., dict[str, Any]] = run_b_boundary_gate,
    isolation_runner: Callable[..., dict[str, Any]] = run_isolation_probe,
) -> dict[str, Any]:
    ledger = EvidenceLedger.create(evidence_root, label)
    rows: list[dict[str, Any]] = []
    try:
        for cohort in COHORTS:
            for case in TRACK1_CASES:
                observed = context_runner(
                    cohort=cohort,
                    seed=case["seed"],
                    record_count=case["record_count"],
                    value_bytes=case["value_bytes"],
                    requested_indexes=case["requested_indexes"],
                )
                for row in observed:
                    row["case"] = case["id"]
                    ledger.append(row)
                rows.extend(observed)

        track2 = boundary_runner(cohort=TRACK2_GATE_COHORT, seed=TRACK2_GATE_SEED)
        for row in track2["rows"]:
            ledger.append(row)
        rows.extend(track2["rows"])
        if track2["expanded"]:
            confirmation: list[dict[str, Any]] = []
            record_count = int(track2["first_red_record_count"])
            for cohort in COHORTS:
                for seed in TRACK2_CONFIRMATION_SEEDS:
                    observed = context_runner(
                        cohort=cohort,
                        seed=seed,
                        record_count=record_count,
                        value_bytes=128,
                        requested_indexes=(record_count - 1,),
                        arms=("B", "D"),
                    )
                    for row in observed:
                        row.update(
                            track="selective_access",
                            case="confirmation",
                            record_count=record_count,
                        )
                        ledger.append(row)
                    confirmation.extend(observed)
                    rows.extend(observed)
            expected = len(COHORTS) * len(TRACK2_CONFIRMATION_SEEDS)
            d_rows = [row for row in confirmation if row["arm"] == "D"]
            b_rows = [row for row in confirmation if row["arm"] == "B"]
            valid = (
                len(d_rows) == expected
                and len(b_rows) == expected
                and all(row["valid_observation"] for row in confirmation)
            )
            replicated_red = (
                valid
                and all(row["external_oracle"] for row in d_rows)
                and all(not row["external_oracle"] for row in b_rows)
            )
            track2["disposition"] = (
                "IMPLEMENTATION OPPORTUNITY" if replicated_red else "INCONCLUSIVE"
            )

        isolation_rows = []
        for cohort in COHORTS:
            for relationship in TRACK3_RELATIONSHIPS:
                row = isolation_runner(
                    cohort=cohort, seed=TRACK3_SEED, relationship=relationship
                )
                ledger.append(row)
                rows.append(row)
                isolation_rows.append(row)

        receipt = {
            "freeze_id": "SCR-V7-INITIAL-2026-09-02",
            "repetition_protocol": "SCR-V7-REPETITION-001-2026-09-03",
            "tracks": {
                "context_cost": {
                    "executed": True,
                    **decide_track1([
                        row for row in rows if row.get("track") == "context_cost"
                    ]),
                },
                "selective_access": {
                    "executed": True,
                    "expanded": track2["expanded"],
                    "disposition": track2["disposition"],
                },
                "isolation": {"executed": True, **decide_track3(isolation_rows)},
                "active_writes": {
                    "executed": False,
                    "gate": "no real workflow witness",
                },
                "concurrency": {"executed": False, "gate": "active-writes gate closed"},
                "remote_backends": {
                    "executed": False,
                    "gate": "no local treatment value",
                },
            },
            "observation_count": len(rows),
            "rows": [public_row(row) for row in rows],
        }
        (ledger.directory / "receipt.json").write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return receipt
    except Exception as exc:
        ledger.abort({
            "type": type(exc).__name__,
            "message": str(exc),
            "retained_observations": len(rows),
        })
        raise
