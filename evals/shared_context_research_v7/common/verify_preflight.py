"""Verify the published provider-free V7 preflight receipt."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def verify(receipt_path: Path) -> None:
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["freeze_id"] == "SCR-V7-INITIAL-2026-09-02"
    assert receipt["hermes_revision"] == ("593aa74c6182ce2e5e23bc102daaaae71710c05d")
    assert receipt["kind"] == "provider_free_preflight"
    assert receipt["observation_count"] == 6
    rows = {row["case"]: row for row in receipt["rows"]}
    assert len(rows) == 6
    assert len({row["isolation_id"] for row in rows.values()}) == 6

    subset = rows["context_subset"]
    assert subset["full_result_exact"] is True
    assert subset["declared_result_exact"] is True
    assert subset["declared_payload_bytes"] < subset["full_payload_bytes"]

    control = rows["context_all_records"]
    assert control["full_result_exact"] is True
    assert control["declared_result_exact"] is True
    assert control["declared_payload_bytes"] == control["full_payload_bytes"]

    above = rows["selective_above_cap"]
    assert above["startup_contains_requested_value"] is False
    assert above["kanban_show_result_exact"] is True
    assert above["current_hermes_red"] is False
    assert above["disposition"] == "EXISTING HERMES MECHANISM SUFFICIENT"

    below = rows["selective_below_cap"]
    assert below["startup_contains_requested_value"] is True
    assert below["kanban_show_result_exact"] is True

    unrelated = rows["isolation_unrelated"]
    assert unrelated["visible"] is True
    assert unrelated["candidate_policy_allows"] is False
    assert unrelated["security_label"] == "POLICY_UNADJUDICATED"
    assert unrelated["is_vulnerability"] is False

    parent = rows["isolation_declared_parent"]
    assert parent["visible"] is True
    assert parent["candidate_policy_allows"] is True
    assert parent["security_label"] == "POSITIVE_CONTROL"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("receipt")
    args = parser.parse_args()
    verify(Path(args.receipt).resolve())
    print("V7 provider-free preflight verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
