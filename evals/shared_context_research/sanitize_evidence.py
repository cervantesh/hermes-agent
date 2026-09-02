"""Create a privacy-safe evidence packet from private raw observations."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .analysis import final_verdict, pilot_expansion_gate
from .runner import verify_seal


PATH_OR_SECRET = re.compile(
    r"(?:[A-Za-z]:\\|/home/|/Users/|/tmp/|D:\\Temp|api[_-]?key|bearer\s)",
    re.IGNORECASE,
)


def _token_receipt(tokens: dict[str, Any] | None) -> dict[str, Any]:
    source = tokens or {}
    allowed = (
        "api_call_count",
        "input_tokens",
        "output_tokens",
        "cache_read_tokens",
        "cache_write_tokens",
        "reasoning_tokens",
        "total_tokens",
        "estimated_cost_usd",
    )
    return {
        key: source[key] for key in allowed if isinstance(source.get(key), (int, float))
    }


def sanitize_record(record: dict[str, Any]) -> dict[str, Any]:
    producer = record.get("producer") or {}
    consumer = record.get("consumer") or {}
    return {
        "task": record["task"],
        "arm": record["arm"],
        "topology": record["topology"],
        "dependent": bool(record["dependent"]),
        "schedule_seed": int(record["schedule_seed"]),
        "model": record["model"],
        "provider": record["provider"],
        "target_head": record["target_head"],
        "protocol_sha256": record["protocol_sha256"],
        "ok": bool(record["ok"]),
        "false_success": bool(record["false_success"]),
        "scope_expansion": bool(record["scope_expansion"]),
        "handoff_fidelity": bool(record.get("handoff_fidelity", True)),
        "producer_checks": producer.get("checks") or {},
        "consumer_checks": consumer.get("checks") or {},
        "context_manifest": record.get("context_manifest") or {},
        "context_receipts": record.get("context_receipts") or [],
        "producer_tokens": _token_receipt(producer.get("tokens")),
        "consumer_tokens": _token_receipt(consumer.get("tokens")),
        "parent_tokens": _token_receipt(record.get("parent_tokens")),
        "total_tokens": record.get("total_tokens"),
        "duration_seconds": record.get("duration_seconds"),
        "expected_digest": record.get("expected_digest"),
        "result_digest": record.get("result_digest"),
        "attempts": record.get("attempts", 1),
    }


def verify_sanitized(records: list[dict[str, Any]]) -> None:
    identities = {
        (row["target_head"], row["protocol_sha256"], row["model"], row["provider"])
        for row in records
    }
    if len(identities) != 1:
        raise ValueError(f"mixed evidence identities: {identities}")
    material = json.dumps(records, ensure_ascii=False)
    if PATH_OR_SECRET.search(material):
        raise ValueError(
            "sanitized packet still contains path or secret-shaped material"
        )
    forbidden = {
        "summary",
        "log",
        "tool_trace",
        "session_id",
        "metadata",
        "consumer_files",
    }
    for row in records:
        overlap = forbidden.intersection(row)
        if overlap:
            raise ValueError(f"forbidden raw fields in receipt: {sorted(overlap)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--expanded", action="store_true")
    args = parser.parse_args()
    raw_path = Path(args.raw).resolve()
    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    raw = [
        json.loads(line)
        for line in raw_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    records = [sanitize_record(row) for row in raw]
    verify_sanitized(records)
    receipt = output / "observations.jsonl"
    receipt.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in records),
        encoding="utf-8",
    )
    seal = verify_seal()
    meta = {
        "target_revision": seal["target_revision"],
        "protocol_sha256": seal["files"]["PROTOCOL_FREEZE.md"],
        "raw_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        "observations_sha256": hashlib.sha256(receipt.read_bytes()).hexdigest(),
        "observation_count": len(records),
        "pilot_gate": pilot_expansion_gate(records),
        "decision": final_verdict(records, expanded=args.expanded),
    }
    (output / "receipt.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(meta, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
