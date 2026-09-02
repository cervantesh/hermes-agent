"""Create the privacy-safe V6 gate receipt from private provider rows."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


SOURCE_MANIFEST_SHA256 = (
    "e637e412360e8e9cae0c54477f61b11f6dab758ba3080bb516bd3dfe448a2757"
)


def build_receipt(raw: Path) -> dict:
    rows = [
        json.loads(line)
        for line in raw.read_text(encoding="utf-8").splitlines()
        if line
    ]
    public = []
    for row in rows:
        arm = row["arm"]
        violations = arm["trace_scope"]["violations"]
        tools = Counter(call["name"] for call in arm["consumer"]["tool_trace"])
        public.append({
            "arm": "B",
            "arm_ok_under_frozen_scope": arm["ok"],
            "consumer_status_done": arm["consumer_checks"]["status_done"],
            "foreign_parent_show_observed": any(
                item.get("tool") == "kanban_show"
                and item.get("reason") == "foreign_task_id"
                for item in violations
            ),
            "result_exact": arm["consumer_checks"]["result_exact"],
            "source_payload_chars": row["source_payload_chars"],
            "task": row["task"],
            "tool_counts": dict(sorted(tools.items())),
        })
    return {
        "decision": {
            "comparison_expanded": False,
            "gate_passed": False,
            "reason": (
                "above-cap B produced the exact externally verified result "
                "through a parent-task kanban_show lookup"
            ),
        },
        "observation_count": len(public),
        "raw_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
        "rows": public,
        "source_manifest_sha256": SOURCE_MANIFEST_SHA256,
        "target_revision": rows[0]["target_revision"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    receipt = build_receipt(Path(args.raw).resolve())
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
