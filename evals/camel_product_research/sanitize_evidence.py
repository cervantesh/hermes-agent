"""Export privacy-safe, row-level receipts from local research JSONL."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


_TOP_LEVEL_FIELDS = (
    "task",
    "cohort",
    "strategy",
    "ok",
    "false_success",
    "checks",
    "status",
    "exit_reason",
    "api_calls",
    "tokens",
    "duration_seconds",
    "label",
    "rep",
    "provider",
    "model",
    "schedule_seed",
    "head",
    "dirty",
    "tree_digest",
)
_PROTOCOL_FIELDS = (
    "specified_task",
    "termination",
    "message_count",
    "prompt_hashes",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sanitize_record(record: dict) -> dict:
    sanitized = {field: record.get(field) for field in _TOP_LEVEL_FIELDS}
    protocol = record.get("protocol")
    sanitized["protocol"] = (
        {field: protocol.get(field) for field in _PROTOCOL_FIELDS}
        if isinstance(protocol, dict)
        else None
    )
    return sanitized


def export(source: Path, output: Path) -> dict:
    records = [
        json.loads(line)
        for line in source.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(
            json.dumps(sanitize_record(record), ensure_ascii=False, sort_keys=True)
            + "\n"
            for record in records
        ),
        encoding="utf-8",
        newline="\n",
    )
    metadata = {
        "source_sha256": _sha256(source),
        "evidence_sha256": _sha256(output),
        "records": len(records),
        "included_fields": list(_TOP_LEVEL_FIELDS),
        "included_protocol_fields": list(_PROTOCOL_FIELDS),
        "excluded_sensitive_fields": [
            "repo",
            "camel_repo",
            "summary",
            "error",
            "tool_trace",
            "protocol.messages",
        ],
    }
    metadata_path = output.with_suffix(".meta.json")
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(export(args.source, args.output), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
