"""Execute only the V7 tracks left unresolved after Run 002."""

from __future__ import annotations

from collections.abc import Callable
import json
from pathlib import Path
from typing import Any

from ..common.evidence import EvidenceLedger
from ..protocol import (
    COHORTS,
    TRACK2_CONFIRMATION_SEEDS,
    TRACK2_GATE_COHORT,
    TRACK2_GATE_SEED,
    TRACK3_RELATIONSHIPS,
    TRACK3_SEED,
)
from ..repetition.study import decide_track3, public_row
from .runners import run_b_boundary_gate, run_context_case, run_isolation_probe


def run_repetition2(
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
                    cohort=cohort,
                    seed=TRACK3_SEED,
                    relationship=relationship,
                )
                ledger.append(row)
                rows.append(row)
                isolation_rows.append(row)

        receipt = {
            "freeze_id": "SCR-V7-INITIAL-2026-09-02",
            "repetition_protocol": "SCR-V7-REPETITION-002-2026-09-03",
            "tracks": {
                "context_cost": {
                    "executed": False,
                    "repeated": False,
                    "source": "v7-repetition-001-20260903",
                    "disposition": "INCONCLUSIVE",
                    "reason": "all-records control closed the Track 1 claim",
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
                "concurrency": {
                    "executed": False,
                    "gate": "active-writes gate closed",
                },
                "remote_backends": {
                    "executed": False,
                    "gate": "no local treatment value",
                },
            },
            "observation_count": len(rows),
            "rows": [
                {
                    **public_row(row),
                    "configured_toolsets": row.get("configured_toolsets", []),
                }
                for row in rows
            ],
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
