"""Audit the second corrected V7 repetition without widening its claims."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from toolsets import resolve_toolset


def _read_rows(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def audit(run_directory: Path) -> dict[str, Any]:
    rows = _read_rows(run_directory / "observations.jsonl")
    receipt = json.loads((run_directory / "receipt.json").read_text(encoding="utf-8"))
    track2 = [row for row in rows if row["track"] == "selective_access"]
    track3 = [row for row in rows if row["track"] == "isolation"]
    positives = [
        row for row in track3 if row["relationship"] == "declared_completed_parent"
    ]
    unrelated = [row for row in track3 if row["relationship"] == "unrelated_same_board"]
    largest = [row for row in track2 if row["record_count"] == 512]
    cli_tools = set(resolve_toolset("hermes-cli"))

    return {
        "freeze_id": receipt["freeze_id"],
        "protocol_id": receipt["repetition_protocol"],
        "run_id": run_directory.name,
        "observation_count": len(rows),
        "receipt_observation_count": receipt["observation_count"],
        "aborted": (run_directory / "ABORTED.json").exists(),
        "all_rows_have_canonical_prompt_tokens": all(
            row["prompt_tokens"]
            == row["input_tokens"]
            + row["cache_read_tokens"]
            + row["cache_write_tokens"]
            for row in rows
        ),
        "strong_baseline_contract": {
            "configured_toolsets": sorted({
                tuple(row["configured_toolsets"]) for row in track2
            }),
            "required_tools_resolve": all(
                name in cli_tools
                for name in ("kanban_show", "kanban_complete", "terminal", "read_file")
            ),
            "largest_case_used_spill_recovery": len(largest) == 1
            and largest[0]["tool_counts"].get("read_file", 0) >= 1
            and largest[0]["tool_counts"].get("terminal", 0) >= 1,
        },
        "track2": {
            "count": len(track2),
            "record_counts": [row["record_count"] for row in track2],
            "all_valid_and_exact": all(
                row["valid_observation"] and row["external_oracle"] for row in track2
            ),
            "confirmation_count": sum(
                row.get("case") == "confirmation" for row in track2
            ),
            "receipt_disposition": receipt["tracks"]["selective_access"]["disposition"],
            "adjudicated_disposition": "EXISTING HERMES MECHANISM SUFFICIENT",
        },
        "track3": {
            "count": len(track3),
            "positive_controls_valid_and_exact": len(positives) == 2
            and all(
                row["valid_observation"] and row["external_oracle"] for row in positives
            ),
            "unrelated_rows_valid_and_visible": len(unrelated) == 2
            and all(
                row["valid_observation"] and row["external_oracle"] for row in unrelated
            ),
            "all_rows_have_durable_current_worker_outcome": all(
                row["outcome_source"] == "task.result" and row["task_status"] == "done"
                for row in track3
            ),
            "receipt_disposition": receipt["tracks"]["isolation"]["disposition"],
            "policy_status": receipt["tracks"]["isolation"].get("policy_status"),
            "is_vulnerability": any(row["is_vulnerability"] for row in track3),
        },
        "adjudicated_tracks": {
            "context_cost": "INCONCLUSIVE_CONTROL_ARTIFACT",
            "selective_access": "EXISTING_HERMES_MECHANISM_SUFFICIENT",
            "isolation": "INCONCLUSIVE_POLICY_UNADJUDICATED",
            "active_writes": "GATE_CLOSED_NOT_EXECUTED",
            "concurrency": "GATE_CLOSED_NOT_EXECUTED",
            "remote_backends": "GATE_CLOSED_NOT_EXECUTED",
        },
        "overall_disposition": "NO_IMPLEMENTATION_JUSTIFIED_BY_FROZEN_EVIDENCE",
        "implementation_authorized": False,
        "bounded_conclusion": (
            "The frozen V7 evidence does not demonstrate incremental product value "
            "for a new CAMEL-derived shared-context implementation in Hermes."
        ),
        "non_conclusions": [
            "CAMEL-derived mechanisms can never help Hermes",
            "same-board unrelated-task visibility is a vulnerability",
            "unexecuted Tracks 4-6 are safe or unnecessary in every future workflow",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_directory")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = audit(Path(args.run_directory).resolve())
    Path(args.output).resolve().write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
