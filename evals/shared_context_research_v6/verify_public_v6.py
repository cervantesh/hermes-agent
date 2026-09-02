"""Verify the privacy-safe V6 gate receipt and stopping rule."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main() -> int:
    receipt = json.loads(
        (ROOT / "evidence" / "v6-cap-gate-20260902" / "receipt.json").read_text(
            encoding="utf-8"
        )
    )
    rows = {row["task"]: row for row in receipt["rows"]}
    below = rows["cap_below_control"]
    above = rows["cap_above_tail_dependency"]
    assert receipt["target_revision"] == ("c7429f60cadb21482c1e3e34ccf4f1014d887de8")
    assert receipt["observation_count"] == 2
    assert below["source_payload_chars"] < 4096
    assert above["source_payload_chars"] > 4096
    assert below["result_exact"] is True
    assert above["result_exact"] is True
    assert above["foreign_parent_show_observed"] is True
    assert receipt["decision"]["gate_passed"] is False
    assert receipt["decision"]["comparison_expanded"] is False
    print("V6 public receipt verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
