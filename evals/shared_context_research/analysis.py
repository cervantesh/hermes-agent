"""Frozen expansion and final-decision calculations."""

from __future__ import annotations

from collections import defaultdict
from statistics import median
from typing import Any, Iterable


PILOT_DEPENDENT = (
    "compact_release_map",
    "ordered_dependency_plan",
    "artifact_policy_join",
    "distractor_filtered_catalog",
)
CONFIRM_DEPENDENT = PILOT_DEPENDENT + (
    "multi_key_reconciliation",
    "bounded_payload_edge",
)


def _pair(records: Iterable[dict[str, Any]]) -> dict[tuple[str, int], dict[str, dict]]:
    paired: dict[tuple[str, int], dict[str, dict]] = defaultdict(dict)
    for record in records:
        paired[(str(record["task"]), int(record["schedule_seed"]))][
            str(record["arm"])
        ] = record
    return dict(paired)


def _improvement(b: float | int | None, c: float | int | None) -> float | None:
    if b is None or c is None or b <= 0:
        return None
    return 100.0 * (float(b) - float(c)) / float(b)


def _resource_median(
    pairs: dict[tuple[str, int], dict[str, dict]],
    tasks: tuple[str, ...],
    seed: int,
    field: str,
) -> float | None:
    values: list[float] = []
    for task in tasks:
        arms = pairs.get((task, seed), {})
        if set(arms) < {"B", "C"}:
            return None
        value = _improvement(arms["B"].get(field), arms["C"].get(field))
        if value is None:
            return None
        values.append(value)
    return median(values)


def pilot_expansion_gate(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    pairs = _pair(records)
    correctness = []
    fidelity = []
    invalid_pairs: list[str] = []
    for task in PILOT_DEPENDENT:
        arms = pairs.get((task, 377), {})
        if set(arms) < {"A", "B", "C"}:
            return {"expand": False, "complete": False, "reason": "missing_pair"}

        def producer_checks(record: dict[str, Any]) -> dict[str, bool]:
            return (record.get("producer") or {}).get("checks", {}) or record.get(
                "producer_checks", {}
            )

        if any(not all(producer_checks(arms[arm]).values()) for arm in ("A", "B", "C")):
            invalid_pairs.append(task)
            continue
        correctness.append(
            (not arms["A"]["ok"] or not arms["B"]["ok"]) and arms["C"]["ok"]
        )
        fidelity.append(
            not arms["B"].get("handoff_fidelity", False)
            and arms["C"].get("handoff_fidelity", False)
        )
    if invalid_pairs:
        return {
            "expand": False,
            "complete": False,
            "reason": "producer_validation_invalidated_pairs",
            "invalid_pairs": invalid_pairs,
        }
    token_delta = _resource_median(pairs, PILOT_DEPENDENT, 377, "total_tokens")
    latency_delta = _resource_median(pairs, PILOT_DEPENDENT, 377, "duration_seconds")
    token_trigger = bool(
        token_delta is not None
        and token_delta >= 15.0
        and (latency_delta is None or latency_delta >= 0.0)
    )
    latency_trigger = bool(
        latency_delta is not None
        and latency_delta >= 20.0
        and (token_delta is None or token_delta >= 0.0)
    )
    triggers = {
        "correctness": any(correctness),
        "fidelity": any(fidelity),
        "tokens": token_trigger,
        "latency": latency_trigger,
    }
    return {
        "expand": any(triggers.values()),
        "complete": True,
        "triggers": triggers,
        "median_token_improvement_pct": token_delta,
        "median_latency_improvement_pct": latency_delta,
    }


def final_verdict(records: Iterable[dict[str, Any]], expanded: bool) -> dict[str, Any]:
    rows = list(records)
    pairs = _pair(rows)
    controls_ok = all(row["ok"] for row in rows if not row.get("dependent"))
    integrity_ok = controls_ok and all(
        not row.get("scope_expansion") and not row.get("provider_failure")
        for row in rows
    )
    if not expanded:
        gate = pilot_expansion_gate(rows)
        if not gate.get("complete") or not integrity_ok:
            return {
                "verdict": "INCONCLUSIVE",
                "integrity_ok": integrity_ok,
                "gate": gate,
            }
        return {
            "verdict": "NO OPPORTUNITY" if not gate["expand"] else "INCONCLUSIVE",
            "integrity_ok": integrity_ok,
            "gate": gate,
        }

    c_only = 0
    b_only = 0
    for seed in (377, 378):
        for task in CONFIRM_DEPENDENT:
            arms = pairs.get((task, seed), {})
            if set(arms) < {"B", "C"}:
                return {
                    "verdict": "INCONCLUSIVE",
                    "reason": "missing_confirmation_pair",
                }
            c_only += int(arms["C"]["ok"] and not arms["B"]["ok"])
            b_only += int(arms["B"]["ok"] and not arms["C"]["ok"])
    token = {
        seed: _resource_median(pairs, CONFIRM_DEPENDENT, seed, "total_tokens")
        for seed in (377, 378)
    }
    latency = {
        seed: _resource_median(pairs, CONFIRM_DEPENDENT, seed, "duration_seconds")
        for seed in (377, 378)
    }
    opposite = any(
        values[377] is not None
        and values[378] is not None
        and values[377] * values[378] < 0
        and abs(values[377]) >= 10
        and abs(values[378]) >= 10
        for values in (token, latency)
    )
    if not integrity_ok or b_only and c_only or opposite:
        verdict = "INCONCLUSIVE"
    elif c_only >= 3 and b_only == 0:
        verdict = "IMPLEMENTATION OPPORTUNITY"
    else:
        token_win = all(value is not None and value >= 15 for value in token.values())
        latency_win = all(
            value is not None and value >= 20 for value in latency.values()
        )
        token_nonregress = all(value is None or value >= 0 for value in token.values())
        latency_nonregress = all(
            value is None or value >= 0 for value in latency.values()
        )
        if (token_win and latency_nonregress) or (latency_win and token_nonregress):
            verdict = "IMPLEMENTATION OPPORTUNITY"
        else:
            verdict = "EXISTING HANDOFF SUFFICIENT"
    return {
        "verdict": verdict,
        "integrity_ok": integrity_ok,
        "c_only_successes": c_only,
        "b_only_successes": b_only,
        "median_token_improvement_pct": token,
        "median_latency_improvement_pct": latency,
    }
