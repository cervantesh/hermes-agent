"""Prospectively declared V3 cross-cohort adjudication."""

from __future__ import annotations

from statistics import median
from typing import Any, Iterable

from .protocol_v3 import COHORTS, CONTROLS, DEPENDENT, TASKS


def _valid(row: dict[str, Any]) -> bool:
    integrity = row.get("integrity") or {}
    return bool(
        not row.get("provider_failure")
        and (not row.get("dependent") or row.get("producer_admitted") is True)
        and set(row.get("arms") or {}) == {"A", "B", "C"}
        and integrity
        and all(value is True for value in integrity.values())
    )


def _improvement(b: float | int, c: float | int) -> float:
    return 100.0 * (float(b) - float(c)) / float(b)


def adjudicate_v3(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    material = list(rows)
    keys = [(row.get("cohort"), row.get("task")) for row in material]
    duplicates = sorted(
        f"{cohort}/{task}"
        for cohort, task in set(keys)
        if keys.count((cohort, task)) > 1
    )
    indexed = dict(zip(keys, material, strict=True))
    expected = {(cohort.id, task) for cohort in COHORTS for task in TASKS}
    unexpected = sorted(f"{cohort}/{task}" for cohort, task in set(indexed) - expected)
    missing = sorted(f"{cohort}/{task}" for cohort, task in expected - set(indexed))
    invalid = sorted(
        f"{cohort}/{task}"
        for (cohort, task), row in indexed.items()
        if (cohort, task) in expected and not _valid(row)
    )
    if missing or invalid or duplicates or unexpected:
        return {
            "verdict": "INCONCLUSIVE",
            "complete": False,
            "missing": missing,
            "invalid": invalid,
            "duplicates": duplicates,
            "unexpected": unexpected,
        }

    controls_ok = all(
        all(indexed[(cohort.id, task)]["arms"][arm]["ok"] for arm in "ABC")
        for cohort in COHORTS
        for task in CONTROLS
    )
    if not controls_ok:
        return {
            "verdict": "INCONCLUSIVE",
            "complete": True,
            "controls_ok": False,
        }

    c_only_by_cohort: dict[str, list[str]] = {}
    b_only_by_cohort: dict[str, list[str]] = {}
    token_medians: dict[str, float] = {}
    latency_medians: dict[str, float] = {}
    for cohort in COHORTS:
        c_only_by_cohort[cohort.id] = []
        b_only_by_cohort[cohort.id] = []
        token_values = []
        latency_values = []
        for task in DEPENDENT:
            arms = indexed[(cohort.id, task)]["arms"]
            if arms["C"]["ok"] and not arms["A"]["ok"] and not arms["B"]["ok"]:
                c_only_by_cohort[cohort.id].append(task)
            if arms["B"]["ok"] and not arms["C"]["ok"]:
                b_only_by_cohort[cohort.id].append(task)
            token_values.append(
                _improvement(arms["B"]["total_tokens"], arms["C"]["total_tokens"])
            )
            latency_values.append(
                _improvement(
                    arms["B"]["duration_seconds"], arms["C"]["duration_seconds"]
                )
            )
        token_medians[cohort.id] = median(token_values)
        latency_medians[cohort.id] = median(latency_values)

    replicated_c_only = sorted(
        set.intersection(*(set(values) for values in c_only_by_cohort.values()))
    )
    token_trigger = all(value >= 15.0 for value in token_medians.values()) and all(
        value >= 0.0 for value in latency_medians.values()
    )
    latency_trigger = all(value >= 20.0 for value in latency_medians.values()) and all(
        value >= 0.0 for value in token_medians.values()
    )
    opportunity = bool(replicated_c_only or token_trigger or latency_trigger)
    any_unreplicated = any(c_only_by_cohort.values())
    verdict = (
        "IMPLEMENTATION OPPORTUNITY"
        if opportunity
        else "INCONCLUSIVE"
        if any_unreplicated
        else "NO DEMONSTRATED INCREMENT"
    )
    return {
        "verdict": verdict,
        "complete": True,
        "controls_ok": True,
        "replicated_c_only": replicated_c_only,
        "c_only_by_cohort": c_only_by_cohort,
        "b_only_by_cohort": b_only_by_cohort,
        "median_token_improvement_pct": token_medians,
        "median_latency_improvement_pct": latency_medians,
        "token_trigger": token_trigger,
        "latency_trigger": latency_trigger,
    }
