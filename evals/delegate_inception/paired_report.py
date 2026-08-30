"""Summarize paired A/B outcomes as wins, losses, draws, and exact McNemar p."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path

from runner import EVAL_DIR


def exact_mcnemar_p(baseline_only: int, candidate_only: int) -> float:
    """Two-sided exact binomial McNemar p-value for discordant pairs."""
    discordant = baseline_only + candidate_only
    if discordant == 0:
        return 1.0
    smaller = min(baseline_only, candidate_only)
    tail = sum(math.comb(discordant, k) for k in range(smaller + 1)) / (
        2**discordant
    )
    return min(1.0, 2 * tail)


def _load(label: str) -> dict[tuple[str, int, str], dict]:
    rows = {}
    for path in sorted((EVAL_DIR / "results" / label).glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            key = (record["task"], record["rep"], record["model"])
            rows[key] = record
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline_label")
    parser.add_argument("candidate_label")
    args = parser.parse_args()

    baseline = _load(args.baseline_label)
    candidate = _load(args.candidate_label)
    if baseline.keys() != candidate.keys():
        missing_candidate = sorted(baseline.keys() - candidate.keys())
        missing_baseline = sorted(candidate.keys() - baseline.keys())
        raise SystemExit(
            "unpaired observations: "
            f"missing candidate={missing_candidate}; missing baseline={missing_baseline}"
        )

    grouped: dict[str, list[tuple[dict, dict]]] = defaultdict(list)
    for key in sorted(baseline):
        left, right = baseline[key], candidate[key]
        grouped[left.get("category", "uncategorized")].append((left, right))
        grouped["ALL"].append((left, right))

    print("category             base  cand  base-only  cand-only  same   p-exact")
    print("-" * 76)
    for category in [name for name in sorted(grouped) if name != "ALL"] + ["ALL"]:
        pairs = grouped[category]
        base_pass = sum(bool(left["ok"]) for left, _ in pairs)
        cand_pass = sum(bool(right["ok"]) for _, right in pairs)
        base_only = sum(bool(left["ok"]) and not right["ok"] for left, right in pairs)
        cand_only = sum(not left["ok"] and bool(right["ok"]) for left, right in pairs)
        same = len(pairs) - base_only - cand_only
        print(
            f"{category:<20}{base_pass:>3}/{len(pairs):<3}"
            f"{cand_pass:>5}/{len(pairs):<3}{base_only:>10}{cand_only:>11}"
            f"{same:>7}{exact_mcnemar_p(base_only, cand_only):>10.4f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
