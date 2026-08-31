"""Reproduce compact descriptive statistics from ignored JSONL observations."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path


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
                str((item.get("protocol") or {}).get("termination") or item.get("exit_reason"))
                for item in records
            )
        ),
    }


def paired(baseline: list[dict], candidate: list[dict]) -> dict:
    left = {item["task"]: item for item in baseline}
    right = {item["task"]: item for item in candidate}
    tasks = sorted(left.keys() & right.keys())
    comparisons = []
    for task in tasks:
        base = left[task]
        cand = right[task]
        base_calls = int(base.get("api_calls") or 0)
        base_duration = float(base.get("duration_seconds") or 0)
        comparisons.append(
            {
                "task": task,
                "baseline_ok": bool(base.get("ok")),
                "candidate_ok": bool(cand.get("ok")),
                "candidate_false_success": bool(cand.get("false_success")),
                "api_call_ratio": round(
                    int(cand.get("api_calls") or 0) / base_calls, 2
                )
                if base_calls
                else None,
                "latency_ratio": round(
                    float(cand.get("duration_seconds") or 0) / base_duration, 2
                )
                if base_duration
                else None,
            }
        )
    base_summary = summarize([left[task] for task in tasks])
    candidate_summary = summarize([right[task] for task in tasks])
    return {
        "tasks": comparisons,
        "baseline": base_summary,
        "candidate": candidate_summary,
        "aggregate_api_call_ratio": round(
            candidate_summary["api_calls"] / base_summary["api_calls"], 2
        ),
        "aggregate_latency_ratio": round(
            candidate_summary["duration_seconds"] / base_summary["duration_seconds"], 2
        ),
        "discordance": {
            "baseline_only_success": sum(
                item["baseline_ok"] and not item["candidate_ok"]
                for item in comparisons
            ),
            "candidate_only_success": sum(
                item["candidate_ok"] and not item["baseline_ok"]
                for item in comparisons
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(paired(load(args.baseline), load(args.candidate)), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
