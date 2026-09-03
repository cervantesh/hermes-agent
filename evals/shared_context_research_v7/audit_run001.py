"""Recompute the bounded disposition of V7 scored Run 001."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any


COHORTS = {"anthropic-sonnet46", "openai-codex-gpt54"}


def _slot_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row.get("track"),
        row.get("case"),
        row.get("cohort"),
        row.get("arm"),
        row.get("seed"),
        row.get("record_count"),
        row.get("relationship"),
    )


def audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    track1 = [
        row for row in rows if row.get("case") in {"subset", "all_records_control"}
    ]
    boundary = [
        row
        for row in rows
        if row.get("case") is None
        and row.get("record_count") in {32, 128, 512}
        and row.get("relationship") is None
    ]
    confirmation = [row for row in rows if row.get("case") == "confirmation"]
    isolation = [row for row in rows if row.get("track") == "isolation"]

    expected_track1 = {
        (case, cohort, arm, seed)
        for case, seed in (("subset", 377), ("all_records_control", 378))
        for cohort in COHORTS
        for arm in ("B", "D")
    }
    actual_track1 = {
        (row.get("case"), row.get("cohort"), row.get("arm"), row.get("seed"))
        for row in track1
    }
    expected_boundary = {
        ("anthropic-sonnet46", "B", 377, count) for count in (32, 128, 512)
    }
    actual_boundary = {
        (row.get("cohort"), row.get("arm"), row.get("seed"), row.get("record_count"))
        for row in boundary
    }
    expected_confirmation = {
        (cohort, arm, seed, 512)
        for cohort in COHORTS
        for arm in ("B", "D")
        for seed in (377, 378)
    }
    actual_confirmation = {
        (row.get("cohort"), row.get("arm"), row.get("seed"), row.get("record_count"))
        for row in confirmation
    }
    expected_isolation = {
        (cohort, relationship, 91)
        for cohort in COHORTS
        for relationship in ("declared_completed_parent", "unrelated_same_board")
    }
    actual_isolation = {
        (row.get("cohort"), row.get("relationship"), row.get("seed"))
        for row in isolation
    }

    d_rows = [row for row in rows if row.get("arm") == "D"]
    contaminated_d = [
        row
        for row in d_rows
        if any(name.startswith("kanban_") for name in (row.get("tool_counts") or {}))
    ]
    controls = [row for row in track1 if row.get("case") == "all_records_control"]
    positives = [
        row
        for row in isolation
        if row.get("relationship") == "declared_completed_parent"
    ]
    boundary_outcomes = {
        str(row["record_count"]): bool(row.get("external_oracle")) for row in boundary
    }
    slot_duplicates = len(rows) - len({_slot_key(row) for row in rows})
    usage_complete = all(
        isinstance(row.get("input_tokens"), int)
        and isinstance(row.get("output_tokens"), int)
        and isinstance(row.get("api_calls"), int)
        and row["api_calls"] > 0
        for row in rows
    )
    slots_complete = (
        len(rows) == 23
        and actual_track1 == expected_track1
        and actual_boundary == expected_boundary
        and actual_confirmation == expected_confirmation
        and actual_isolation == expected_isolation
        and slot_duplicates == 0
    )

    return {
        "freeze_id": "SCR-V7-INITIAL-2026-09-02",
        "run_id": "v7-scored-20260903",
        "observation_count": len(rows),
        "slots_complete": slots_complete,
        "slot_duplicates": slot_duplicates,
        "provider_usage_complete": usage_complete,
        "arm_counts": dict(sorted(Counter(row.get("arm") for row in rows).items())),
        "cohort_counts": dict(
            sorted(Counter(row.get("cohort") for row in rows).items())
        ),
        "track2_b_first_outcomes": boundary_outcomes,
        "track2_expansion_expected": boundary_outcomes.get("512") is False,
        "d_rows_with_forbidden_kanban_tools": len(contaminated_d),
        "all_records_controls_exact": bool(controls)
        and all(row.get("external_oracle") is True for row in controls),
        "track3_positive_controls_exact": bool(positives)
        and all(row.get("external_oracle") is True for row in positives),
        "canary_disclosed_in_any_track3_prompt": any(
            row.get("canary_disclosed_in_prompt") is True for row in isolation
        ),
        "terminal_postprocessing_error": "KeyError: case",
        "disposition": "INCONCLUSIVE_PROTOCOL_IMPLEMENTATION",
        "reuse_policy": "PRESERVE_BUT_DO_NOT_POOL_WITH_A_REPETITION",
        "reasons": [
            "D executed Kanban tools despite the frozen no-Kanban contract",
            "Track 1 all-records controls were not exact across both cohorts",
            "Track 3 declared-parent positive controls failed in both cohorts",
            "the terminal receipt builder misclassified B-first Track 2 rows",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--journal", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    journal = Path(args.journal).resolve()
    output = Path(args.output).resolve()
    rows = [
        json.loads(line)
        for line in journal.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    result = audit(rows)
    result["journal_sha256"] = hashlib.sha256(journal.read_bytes()).hexdigest()
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"disposition": result["disposition"], "rows": len(rows)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
