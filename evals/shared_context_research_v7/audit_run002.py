"""Audit the corrected-but-baseline-restricted V7 repetition."""

from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path
from typing import Any

from toolsets import _HERMES_CORE_TOOLS, resolve_toolset

from .repetition import runners


def _read_rows(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def audit(run_directory: Path) -> dict[str, Any]:
    rows = _read_rows(run_directory / "observations.jsonl")
    receipt = json.loads((run_directory / "receipt.json").read_text(encoding="utf-8"))
    source = inspect.getsource(runners.run_context_case)
    kanban_only = 'toolsets = ("kanban",)' in source
    kanban_tools = set(resolve_toolset("kanban"))
    missing_strong_baseline = sorted(
        name
        for name in ("terminal", "read_file")
        if name in _HERMES_CORE_TOOLS and name not in kanban_tools
    )

    confirmation = [row for row in rows if row.get("case") == "confirmation"]
    b_confirmation = [row for row in confirmation if row["arm"] == "B"]
    d_confirmation = [row for row in confirmation if row["arm"] == "D"]
    track3 = [row for row in rows if row["track"] == "isolation"]
    positive = [
        row for row in track3 if row["relationship"] == "declared_completed_parent"
    ]

    return {
        "freeze_id": receipt["freeze_id"],
        "protocol_id": receipt["repetition_protocol"],
        "run_id": run_directory.name,
        "observation_count": len(rows),
        "receipt_observation_count": receipt["observation_count"],
        "all_rows_have_canonical_prompt_tokens": all(
            row["prompt_tokens"]
            == row["input_tokens"]
            + row["cache_read_tokens"]
            + row["cache_write_tokens"]
            for row in rows
        ),
        "all_d_rows_tool_free": all(
            not row["tool_counts"] for row in rows if row.get("arm") == "D"
        ),
        "track1_receipt_disposition": receipt["tracks"]["context_cost"]["disposition"],
        "track1_control_artifact": receipt["tracks"]["context_cost"].get(
            "control_artifact"
        )
        is True,
        "track2_confirmation": {
            "b_count": len(b_confirmation),
            "d_count": len(d_confirmation),
            "all_b_valid_failures": all(
                row["valid_observation"] and not row["external_oracle"]
                for row in b_confirmation
            ),
            "all_d_valid_successes": all(
                row["valid_observation"] and row["external_oracle"]
                for row in d_confirmation
            ),
        },
        "track2_receipt_disposition": receipt["tracks"]["selective_access"][
            "disposition"
        ],
        "b_configured_kanban_only": kanban_only,
        "strong_baseline_tools_missing": missing_strong_baseline,
        "track3_positive_controls_valid_and_exact": all(
            row["valid_observation"] and row["external_oracle"] for row in positive
        ),
        "track3_receipt_disposition": receipt["tracks"]["isolation"]["disposition"],
        "adjudicated_tracks": {
            "context_cost": "INCONCLUSIVE",
            "selective_access": "INCONCLUSIVE",
            "isolation": "INCONCLUSIVE",
            "active_writes": "GATE_CLOSED_NOT_EXECUTED",
            "concurrency": "GATE_CLOSED_NOT_EXECUTED",
            "remote_backends": "GATE_CLOSED_NOT_EXECUTED",
        },
        "overall_disposition": "INCONCLUSIVE_PROTOCOL_IMPLEMENTATION",
        "implementation_authorized": False,
        "reasons": [
            "Track 1's all-records control shows the same resource advantage",
            "Track 2 restricted B to the kanban toolset instead of the frozen strongest-current-Hermes surface",
            "Track 3 did not pass both family-level positive controls",
        ],
        "reuse_policy": "PRESERVE_BUT_DO_NOT_POOL_WITH_A_FURTHER_REPETITION",
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
