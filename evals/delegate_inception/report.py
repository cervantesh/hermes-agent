"""Render comparable totals and per-check failures from evaluation JSONL."""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("labels", nargs="+")
    args = parser.parse_args()
    totals = collections.defaultdict(lambda: [0, 0, 0, 0.0])

    for label in args.labels:
        for path in sorted((EVAL_DIR / "results" / label).glob("*.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                record = json.loads(line)
                key = (label, record["task"])
                totals[key][0] += int(record["ok"])
                totals[key][1] += 1
                totals[key][2] += int(record.get("api_calls") or 0)
                totals[key][3] += float(record.get("duration_seconds") or 0)
                failures = [name for name, ok in record["checks"].items() if not ok]
                if failures:
                    print(
                        f"FAIL {label} rep{record['rep']} {record['task']}: "
                        + ", ".join(failures)
                    )

    print("\nlabel/task                  pass       avg calls   avg seconds")
    print("-" * 68)
    for (label, task), (passed, count, calls, duration) in sorted(totals.items()):
        print(
            f"{label + '/' + task:<28}{passed:>3}/{count:<7}"
            f"{calls / count:>10.1f}{duration / count:>14.1f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
