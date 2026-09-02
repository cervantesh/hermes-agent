"""Frozen V2 pilot gate and product adjudication calculations."""

from __future__ import annotations

from statistics import median
from typing import Any, Iterable

from .protocol_v2 import DEPENDENT, PILOT_DEPENDENT


def _index(
    fixtures: Iterable[dict[str, Any]],
) -> dict[tuple[str, int], dict[str, Any]]:
    return {(str(row["task"]), int(row["schedule_seed"])): row for row in fixtures}


def _improvement(b: float | int | None, c: float | int | None) -> float | None:
    if b is None or c is None or float(b) <= 0:
        return None
    return 100.0 * (float(b) - float(c)) / float(b)


def _fixture_valid(fixture: dict[str, Any]) -> bool:
    integrity = fixture.get("integrity") or {}
    arms = fixture.get("arms") or {}
    return bool(
        not fixture.get("provider_failure")
        and fixture.get("producer_admitted", True)
        and set(arms) == {"A", "B", "C"}
        and integrity
        and all(value is True for value in integrity.values())
    )


def _resource_median(
    indexed: dict[tuple[str, int], dict[str, Any]],
    tasks: tuple[str, ...],
    seed: int,
    field: str,
) -> float | None:
    values: list[float] = []
    for task in tasks:
        fixture = indexed.get((task, seed))
        if fixture is None or not _fixture_valid(fixture):
            return None
        arms = fixture["arms"]
        value = _improvement(arms["B"].get(field), arms["C"].get(field))
        if value is None:
            return None
        values.append(value)
    return median(values)


def pilot_expansion_gate_v2(
    fixtures: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    indexed = _index(fixtures)
    correctness: list[bool] = []
    fidelity: list[bool] = []
    invalid: list[str] = []
    for task in PILOT_DEPENDENT:
        fixture = indexed.get((task, 377))
        if fixture is None:
            return {
                "expand": False,
                "complete": False,
                "reason": "missing_fixture",
                "missing": task,
            }
        if not _fixture_valid(fixture):
            invalid.append(task)
            continue
        arms = fixture["arms"]
        correctness.append(
            (not arms["A"]["ok"] or not arms["B"]["ok"]) and arms["C"]["ok"]
        )
        fidelity.append(
            not arms["B"].get("handoff_fidelity", False)
            and arms["C"].get("handoff_fidelity", False)
        )
    if invalid:
        return {
            "expand": False,
            "complete": False,
            "reason": "invalid_common_producer_pair_or_integrity",
            "invalid_fixtures": invalid,
        }
    token_delta = _resource_median(indexed, PILOT_DEPENDENT, 377, "total_tokens")
    latency_delta = _resource_median(indexed, PILOT_DEPENDENT, 377, "duration_seconds")
    token_trigger = bool(
        token_delta is not None
        and token_delta >= 15.0
        and latency_delta is not None
        and latency_delta >= 0.0
    )
    latency_trigger = bool(
        latency_delta is not None
        and latency_delta >= 20.0
        and token_delta is not None
        and token_delta >= 0.0
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
        "resource_gate_available": token_delta is not None
        and latency_delta is not None,
    }


def final_verdict_v2(
    fixtures: Iterable[dict[str, Any]], *, expanded: bool
) -> dict[str, Any]:
    rows = list(fixtures)
    gate = pilot_expansion_gate_v2(rows)
    controls = [row for row in rows if not row.get("dependent")]
    controls_ok = bool(controls) and all(
        _fixture_valid(row) and all(arm["ok"] for arm in row["arms"].values())
        for row in controls
    )
    if not expanded:
        if not gate.get("complete") or not controls_ok:
            return {
                "verdict": "INCONCLUSIVE",
                "controls_ok": controls_ok,
                "gate": gate,
            }
        return {
            "verdict": "NO OPPORTUNITY" if not gate["expand"] else "INCONCLUSIVE",
            "controls_ok": controls_ok,
            "gate": gate,
        }

    if not gate.get("complete") or not gate.get("expand"):
        return {
            "verdict": "INCONCLUSIVE",
            "reason": "confirmation_without_open_pilot_gate",
            "controls_ok": controls_ok,
            "gate": gate,
        }

    indexed = _index(rows)
    required = [(task, seed) for seed in (377, 378) for task in DEPENDENT]
    missing_or_invalid = [
        f"{task}@{seed}"
        for task, seed in required
        if (task, seed) not in indexed or not _fixture_valid(indexed[(task, seed)])
    ]
    if missing_or_invalid or not controls_ok:
        return {
            "verdict": "INCONCLUSIVE",
            "reason": "missing_or_invalid_confirmation",
            "invalid": missing_or_invalid,
            "controls_ok": controls_ok,
            "gate": gate,
        }

    c_only = 0
    b_only = 0
    c_false_success = 0
    for task, seed in required:
        arms = indexed[(task, seed)]["arms"]
        c_only += int(arms["C"]["ok"] and not arms["B"]["ok"])
        b_only += int(arms["B"]["ok"] and not arms["C"]["ok"])
        c_false_success += int(arms["C"].get("false_success", False))
    token = {
        seed: _resource_median(indexed, DEPENDENT, seed, "total_tokens")
        for seed in (377, 378)
    }
    latency = {
        seed: _resource_median(indexed, DEPENDENT, seed, "duration_seconds")
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
    if (b_only and c_only) or opposite or c_false_success:
        verdict = "INCONCLUSIVE"
    elif c_only >= 3 and b_only == 0:
        verdict = "IMPLEMENTATION OPPORTUNITY"
    else:
        token_win = all(value is not None and value >= 15 for value in token.values())
        latency_win = all(
            value is not None and value >= 20 for value in latency.values()
        )
        token_nonregress = all(
            value is not None and value >= 0 for value in token.values()
        )
        latency_nonregress = all(
            value is not None and value >= 0 for value in latency.values()
        )
        if (token_win and latency_nonregress) or (latency_win and token_nonregress):
            verdict = "IMPLEMENTATION OPPORTUNITY"
        else:
            verdict = "EXISTING HANDOFF SUFFICIENT"
    return {
        "verdict": verdict,
        "controls_ok": controls_ok,
        "gate": gate,
        "c_only_successes": c_only,
        "b_only_successes": b_only,
        "c_false_successes": c_false_success,
        "median_token_improvement_pct": token,
        "median_latency_improvement_pct": latency,
        "material_seed_discordance": opposite,
    }
