"""Create privacy-safe receipts from V2 fixture records."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .analysis_v2 import final_verdict_v2, pilot_expansion_gate_v2
from .provenance_v2 import source_manifest_digest_v2


PATH_OR_SECRET = re.compile(
    r"(?:[A-Za-z]:\\|/home/|/Users/|/tmp/|api[_-]?key|bearer\s)",
    re.IGNORECASE,
)
FORBIDDEN_KEYS = frozenset({
    "body",
    "consumer_files",
    "error",
    "exception",
    "home",
    "log",
    "metadata",
    "preview",
    "resolved",
    "session_id",
    "summary",
    "task_id",
    "tool_trace",
    "workspace",
})


def _numeric_receipt(source: dict[str, Any] | None) -> dict[str, int | float]:
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
    values = source or {}
    return {
        key: values[key]
        for key in allowed
        if isinstance(values.get(key), (int, float))
        and not isinstance(values.get(key), bool)
    }


def _schema_receipt(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "profile": source.get("profile"),
        "provider_override": source.get("provider_override"),
        "model_override": source.get("model_override"),
        "max_iterations": source.get("max_iterations"),
        "config_sha256": source.get("config_sha256"),
        "schema_sha256": source.get("schema_sha256"),
        "tool_names": source.get("tool_names") or [],
        "forbidden_absent": bool(source.get("forbidden_absent")),
        "required_present": bool(source.get("required_present")),
        "surface_bounded": bool(source.get("surface_bounded")),
    }


def _arm_receipt(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "schedule_position": int(source["schedule_position"]),
        "ok": bool(source["ok"]),
        "false_success": bool(source["false_success"]),
        "scope_expansion": bool(source["scope_expansion"]),
        "handoff_fidelity": bool(source["handoff_fidelity"]),
        "consumer_checks": source.get("consumer_checks") or {},
        "context_manifest": source.get("context_manifest") or {},
        "context_receipts": source.get("context_receipts") or [],
        "trace_scope_ok": bool((source.get("trace_scope") or {}).get("ok")),
        "parent_tokens": _numeric_receipt(source.get("parent_tokens")),
        "consumer_tokens": _numeric_receipt(source.get("consumer_tokens")),
        "session_id_source": (source.get("consumer") or {}).get("session_id_source"),
        "common_producer_tokens": source.get("common_producer_tokens"),
        "total_tokens": source.get("total_tokens"),
        "cost_segments": source.get("cost_segments") or {},
        "duration_seconds": source.get("duration_seconds"),
        "expected_digest": source.get("expected_digest"),
        "result_digest": source.get("result_digest"),
        "profile_receipt": _schema_receipt(source.get("profile_receipt") or {}),
        "pre_run_counts": source.get("pre_run_counts") or {},
    }


def sanitize_fixture_v2(record: dict[str, Any]) -> dict[str, Any]:
    """Retain outcome evidence while dropping prompts, paths, IDs, and logs."""

    return {
        "task": record["task"],
        "schedule_seed": int(record["schedule_seed"]),
        "topology": record["topology"],
        "dependent": bool(record["dependent"]),
        "preflight": bool(record.get("preflight")),
        "order": list(record["order"]),
        "target_head": record.get("target_head"),
        "target_dirty": bool(record.get("target_dirty")),
        "provider": record.get("provider"),
        "model": record.get("model"),
        "protocol_sha256": record.get("protocol_sha256"),
        "source_manifest_sha256": record.get("source_manifest_sha256"),
        "attempts": int(record.get("attempts", 1)),
        "producer_admitted": bool(record.get("producer_admitted", True)),
        "producer_checks": record.get("producer_checks") or {},
        "schemas_safe_equal": bool(record.get("schemas_safe_equal")),
        "schemas": {
            arm: _schema_receipt(receipt)
            for arm, receipt in sorted((record.get("schemas") or {}).items())
        },
        "pre_run_counts": record.get("pre_run_counts") or {},
        "common_producer_tokens": record.get("common_producer_tokens"),
        "common_producer_duration_seconds": record.get(
            "common_producer_duration_seconds"
        ),
        "arms": {
            arm: _arm_receipt(receipt)
            for arm, receipt in sorted((record.get("arms") or {}).items())
        },
        "integrity": record.get("integrity") or {},
        "provider_failure": record.get("provider_failure"),
    }


def _walk(value: Any, path: tuple[str, ...] = ()) -> None:
    if isinstance(value, dict):
        overlap = FORBIDDEN_KEYS.intersection(value)
        if overlap:
            raise ValueError(
                f"forbidden raw fields at {'.'.join(path) or '<root>'}: "
                f"{sorted(overlap)}"
            )
        for key, child in value.items():
            _walk(child, (*path, str(key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk(child, (*path, str(index)))


def verify_sanitized_v2(records: list[dict[str, Any]]) -> None:
    if not records:
        raise ValueError("sanitized packet is empty")
    _walk(records)
    material = json.dumps(records, ensure_ascii=False)
    if PATH_OR_SECRET.search(material):
        raise ValueError("sanitized packet contains path- or secret-shaped material")
    heads = {row.get("target_head") for row in records}
    if len(heads) != 1 or None in heads:
        raise ValueError(f"mixed or missing target identities: {heads}")
    if any(row.get("target_dirty") for row in records):
        raise ValueError("a sanitized record targets a dirty checkout")
    provenance = {row.get("source_manifest_sha256") for row in records}
    if len(provenance) != 1 or None in provenance:
        raise ValueError(f"mixed or missing source provenance: {provenance}")


def write_packet_v2(
    raw_path: Path,
    output_dir: Path,
    *,
    expanded: bool,
) -> dict[str, Any]:
    raw = [
        json.loads(line)
        for line in raw_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    manifests = [row.get("source_manifest") for row in raw]
    manifest_digests = {row.get("source_manifest_sha256") for row in raw}
    if (
        any(not isinstance(manifest, dict) or not manifest for manifest in manifests)
        or len({json.dumps(manifest, sort_keys=True) for manifest in manifests}) != 1
        or len(manifest_digests) != 1
        or None in manifest_digests
    ):
        raise ValueError("raw packet has mixed or missing source provenance")
    manifest_digest = source_manifest_digest_v2(manifests[0])
    if manifest_digests != {manifest_digest}:
        raise ValueError("raw source manifest digest mismatch")
    records = [sanitize_fixture_v2(row) for row in raw]
    verify_sanitized_v2(records)
    output_dir.mkdir(parents=True, exist_ok=True)
    observations = output_dir / "observations.jsonl"
    observations.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in records),
        encoding="utf-8",
    )
    meta = {
        "target_revision": records[0]["target_head"],
        "raw_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        "observations_sha256": hashlib.sha256(observations.read_bytes()).hexdigest(),
        "observation_count": len(records),
        "preflight": all(row["preflight"] for row in records),
        "source_manifest": manifests[0],
        "source_manifest_sha256": manifest_digest,
        "pilot_gate": None
        if all(row["preflight"] for row in records)
        else pilot_expansion_gate_v2(records),
        "decision": None
        if all(row["preflight"] for row in records)
        else final_verdict_v2(records, expanded=expanded),
    }
    (output_dir / "receipt.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return meta


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--expanded", action="store_true")
    args = parser.parse_args()
    meta = write_packet_v2(
        Path(args.raw).resolve(),
        Path(args.output_dir).resolve(),
        expanded=args.expanded,
    )
    print(json.dumps(meta, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
