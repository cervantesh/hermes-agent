"""Reproduce compact descriptive statistics from ignored JSONL observations."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path


_COHORT_IDENTITY_FIELDS = (
    "label",
    "provider",
    "model",
    "schedule_seed",
    "head",
    "tree_digest",
)


def load(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def summarize(records: list[dict]) -> dict:
    count = len(records)
    return {
        "n": count,
        "verified": sum(bool(item.get("ok")) for item in records),
        "false_success": sum(bool(item.get("false_success")) for item in records),
        "api_calls": sum(int(item.get("api_calls") or 0) for item in records),
        "duration_seconds": round(
            sum(float(item.get("duration_seconds") or 0) for item in records), 2
        ),
        "terminations": dict(
            Counter(
                str(
                    (item.get("protocol") or {}).get("termination")
                    or item.get("exit_reason")
                )
                for item in records
            )
        ),
    }


def _cohort_identity(records: list[dict], *, strategy: str) -> dict:
    if not records:
        raise ValueError(f"{strategy} cohort is empty")
    identity: dict[str, object] = {}
    seen: set[tuple[str, int]] = set()
    for item in records:
        if item.get("strategy") != strategy:
            raise ValueError(
                f"expected {strategy} record, got {item.get('strategy')!r}"
            )
        key = (str(item.get("task") or ""), int(item.get("rep") or 0))
        if not key[0] or key[1] < 1:
            raise ValueError(f"invalid pair identity: {key!r}")
        if key in seen:
            raise ValueError(f"duplicate pair identity: {key!r}")
        seen.add(key)
        for field in _COHORT_IDENTITY_FIELDS:
            if field not in item or item[field] is None or item[field] == "":
                raise ValueError(f"missing {field} in {strategy} cohort")
            value = item.get(field)
            if field not in identity:
                identity[field] = value
            elif identity[field] != value:
                raise ValueError(
                    f"mixed {field} in {strategy} cohort: "
                    f"{identity[field]!r} != {value!r}"
                )
    return identity


def paired(
    baseline: list[dict],
    candidate: list[dict],
    *,
    tasks: set[str] | None = None,
) -> dict:
    left_identity = _cohort_identity(baseline, strategy="baseline")
    right_identity = _cohort_identity(candidate, strategy="camel")
    for field in ("provider", "model"):
        if left_identity[field] != right_identity[field]:
            raise ValueError(
                f"paired cohorts differ on {field}: "
                f"{left_identity[field]!r} != {right_identity[field]!r}"
            )
    left = {(item["task"], int(item["rep"])): item for item in baseline}
    right = {(item["task"], int(item["rep"])): item for item in candidate}
    if tasks is not None:
        if not tasks:
            raise ValueError("explicit task filter is empty")
        left = {key: value for key, value in left.items() if key[0] in tasks}
        right = {key: value for key, value in right.items() if key[0] in tasks}
        observed = {key[0] for key in left} | {key[0] for key in right}
        if observed != tasks:
            raise ValueError(
                f"explicit task filter not found in both cohorts: {sorted(tasks - observed)!r}"
            )
    if left.keys() != right.keys():
        missing_left = sorted(right.keys() - left.keys())
        missing_right = sorted(left.keys() - right.keys())
        raise ValueError(
            "paired cohorts are incomplete: "
            f"missing_baseline={missing_left!r}, missing_candidate={missing_right!r}"
        )
    tasks = sorted(left)
    comparisons = []
    for task, rep in tasks:
        base = left[(task, rep)]
        cand = right[(task, rep)]
        base_calls = int(base.get("api_calls") or 0)
        base_duration = float(base.get("duration_seconds") or 0)
        comparisons.append({
            "task": task,
            "rep": rep,
            "baseline_ok": bool(base.get("ok")),
            "candidate_ok": bool(cand.get("ok")),
            "candidate_false_success": bool(cand.get("false_success")),
            "api_call_ratio": round(int(cand.get("api_calls") or 0) / base_calls, 2)
            if base_calls
            else None,
            "latency_ratio": round(
                float(cand.get("duration_seconds") or 0) / base_duration, 2
            )
            if base_duration
            else None,
        })
    base_summary = summarize([left[key] for key in tasks])
    candidate_summary = summarize([right[key] for key in tasks])
    return {
        "baseline_identity": left_identity,
        "candidate_identity": right_identity,
        "tasks": comparisons,
        "baseline": base_summary,
        "candidate": candidate_summary,
        "aggregate_api_call_ratio": round(
            candidate_summary["api_calls"] / base_summary["api_calls"], 2
        )
        if base_summary["api_calls"]
        else None,
        "aggregate_latency_ratio": round(
            candidate_summary["duration_seconds"] / base_summary["duration_seconds"], 2
        )
        if base_summary["duration_seconds"]
        else None,
        "discordance": {
            "baseline_only_success": sum(
                item["baseline_ok"] and not item["candidate_ok"] for item in comparisons
            ),
            "candidate_only_success": sum(
                item["candidate_ok"] and not item["baseline_ok"] for item in comparisons
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument(
        "--tasks",
        help="comma-separated explicit paired subset; required when cohort task sets differ",
    )
    args = parser.parse_args()
    tasks = {item for item in (args.tasks or "").split(",") if item} or None
    print(
        json.dumps(
            paired(load(args.baseline), load(args.candidate), tasks=tasks),
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
