"""Audit V4's format-sensitive handoff-fidelity metric semantically."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from evals.shared_context_research.runtime import HANDOFF_CLOSE, HANDOFF_OPEN
from evals.shared_context_research.shared_context import canonical_bytes
from evals.shared_context_research.tasks import TASKS_BY_ID


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _summary_payload(summary: str) -> str:
    value = summary.strip()
    if value.startswith(HANDOFF_OPEN) and value.endswith(HANDOFF_CLOSE):
        return value[len(HANDOFF_OPEN) : -len(HANDOFF_CLOSE)]
    return value


def audit_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for row in rows:
        if not row.get("dependent"):
            continue
        task_id = str(row["task"])
        summary = str(row["producer"]["summary"])
        payload = _summary_payload(summary)
        expected = canonical_bytes(TASKS_BY_ID[task_id].source)
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            parsed = None
        receipts.append({
            "cohort": row["cohort"],
            "task": task_id,
            "producer_summary_sha256": _sha(summary.encode("utf-8")),
            "normalized_payload_sha256": _sha(payload.encode("utf-8")),
            "expected_source_sha256": _sha(expected),
            "parseable_json": parsed is not None,
            "semantic_equal": parsed == TASKS_BY_ID[task_id].source,
            "wrapper_exact_recorded": bool(row["arms"]["B"]["handoff_fidelity"]),
            "b_outcome_ok": bool(row["arms"]["B"]["ok"]),
        })
    return receipts


def build_receipt(raw_path: Path) -> dict[str, Any]:
    rows = [
        json.loads(line)
        for line in raw_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    receipts = audit_rows(rows)
    return {
        "raw_sha256": _sha(raw_path.read_bytes()),
        "dependent_observation_count": len(receipts),
        "semantic_exact_count": sum(row["semantic_equal"] for row in receipts),
        "wrapper_exact_count": sum(row["wrapper_exact_recorded"] for row in receipts),
        "rows": receipts,
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
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
