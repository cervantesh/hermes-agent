"""Sealed staged orchestration for V7 Tracks 1–3."""

from __future__ import annotations

import argparse
from collections.abc import Callable
import json
from pathlib import Path
import subprocess
from typing import Any

from .common.evidence import EvidenceLedger, sanitize_observation, verify_seal
from .common.harness import ResourceResult, resource_gate
from .context_cost.runner import run_case
from .isolation.runner import run_relationship_probe
from .protocol import (
    COHORTS,
    TRACK1_CASES,
    TRACK2_GATE_COHORT,
    TRACK2_GATE_SEED,
    TRACK2_CONFIRMATION_SEEDS,
    TRACK3_RELATIONSHIPS,
    TRACK3_SEED,
    HERMES_REVISION,
)
from .selective_access.runner import run_b_boundary_gate


ROOT = Path(__file__).resolve().parent


def verify_target(repo_root: Path) -> None:
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo_root, text=True
    ).strip()
    if head != HERMES_REVISION:
        raise RuntimeError(f"Hermes target mismatch: {head}")
    status = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=repo_root,
        text=True,
    ).splitlines()
    outside = []
    for line in status:
        path = line[3:].replace("\\", "/")
        if not path.startswith("evals/shared_context_research_v7/"):
            outside.append(line)
    if outside:
        raise RuntimeError("production checkout is dirty outside the V7 package")


def _track1_decision(rows: list[dict[str, Any]]) -> dict[str, Any]:
    subset = [row for row in rows if row["case"] == "subset"]
    control = [row for row in rows if row["case"] == "all_records_control"]
    if len(control) != len(COHORTS) * 2 or not all(
        row["external_oracle"] for row in control
    ):
        return {
            "disposition": "INCONCLUSIVE",
            "reason": "all-records control missing or not exact",
        }
    by_cohort: list[ResourceResult] = []
    for cohort in COHORTS:
        selected = [row for row in subset if row["cohort"] == cohort.id]
        arms = {row["arm"]: row for row in selected}
        if set(arms) != {"B", "D"}:
            return {"disposition": "INCONCLUSIVE", "reason": "missing arm"}
        by_cohort.append(
            ResourceResult(
                cohort=cohort.id,
                external_success_equal=(
                    arms["B"]["external_oracle"] and arms["D"]["external_oracle"]
                ),
                baseline_tokens=arms["B"]["input_tokens"],
                candidate_tokens=arms["D"]["input_tokens"],
                baseline_latency_ms=arms["B"]["latency_ms"],
                candidate_latency_ms=arms["D"]["latency_ms"],
            )
        )
    gate = resource_gate(by_cohort)
    disposition = (
        "IMPLEMENTATION OPPORTUNITY" if gate.passed else "NO DEMONSTRATED INCREMENT"
    )
    return {
        "disposition": disposition,
        "smaller_footprint_discriminant": "#95561" if gate.passed else None,
        "resource_gate": {
            "passed": gate.passed,
            "token_reduction": gate.token_reduction,
            "latency_reduction": gate.latency_reduction,
            "reason": gate.reason,
        },
    }


def run_study(
    *,
    evidence_root: Path,
    label: str,
    context_runner: Callable[..., list[dict[str, Any]]] = run_case,
    boundary_runner: Callable[..., dict[str, Any]] = run_b_boundary_gate,
    isolation_runner: Callable[..., dict[str, Any]] = run_relationship_probe,
    verify_protocol: bool = True,
) -> dict[str, Any]:
    if verify_protocol:
        verify_target(ROOT.parents[1])
        verify_seal(ROOT, ROOT / "PROTOCOL_SEAL.json")
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

        track2 = boundary_runner(
            cohort=TRACK2_GATE_COHORT,
            seed=TRACK2_GATE_SEED,
        )
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
                        row["track"] = "selective_access"
                        row["case"] = "confirmation"
                        row["record_count"] = record_count
                        ledger.append(row)
                    confirmation.extend(observed)
                    rows.extend(observed)
            d_rows = [row for row in confirmation if row["arm"] == "D"]
            b_rows = [row for row in confirmation if row["arm"] == "B"]
            expected_count = len(COHORTS) * len(TRACK2_CONFIRMATION_SEEDS)
            if (
                len(d_rows) == expected_count
                and len(b_rows) == expected_count
                and all(row["external_oracle"] for row in d_rows)
                and all(not row["external_oracle"] for row in b_rows)
            ):
                track2["disposition"] = "IMPLEMENTATION OPPORTUNITY"
            else:
                track2["disposition"] = "INCONCLUSIVE"

        isolation_rows = []
        for cohort in COHORTS:
            for relationship in TRACK3_RELATIONSHIPS:
                row = isolation_runner(
                    cohort=cohort,
                    seed=TRACK3_SEED,
                    relationship=relationship,
                )
                ledger.append(row)
                rows.append(row)
                isolation_rows.append(row)
    except Exception as exc:
        ledger.abort({"type": type(exc).__name__, "message": str(exc)})
        raise

    track1 = _track1_decision([
        row for row in rows if row.get("track") == "context_cost"
    ])
    receipt = {
        "freeze_id": "SCR-V7-INITIAL-2026-09-02",
        "tracks": {
            "context_cost": {"executed": True, **track1},
            "selective_access": {
                "executed": True,
                "expanded": track2["expanded"],
                "disposition": track2["disposition"],
            },
            "isolation": {
                "executed": True,
                "disposition": "POLICY DECISION REQUIRED",
                "rows": [sanitize_observation(row) for row in isolation_rows],
            },
            "active_writes": {"executed": False, "gate": "no real workflow witness"},
            "concurrency": {"executed": False, "gate": "active-writes gate closed"},
            "remote_backends": {"executed": False, "gate": "no local treatment value"},
        },
        "observation_count": len(rows),
        "rows": [sanitize_observation(row) for row in rows],
    }
    (ledger.directory / "receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", required=True)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    receipt = run_study(
        evidence_root=Path(args.evidence_root).resolve(), label=args.label
    )
    print(json.dumps({"observation_count": receipt["observation_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
