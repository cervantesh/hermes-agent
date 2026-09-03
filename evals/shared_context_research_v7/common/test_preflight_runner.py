from __future__ import annotations

from pathlib import Path

from .preflight_runner import run_preflights
from .verify_preflight import verify


def test_preflight_runner_uses_fresh_graphs_and_reports_gate_state(
    tmp_path: Path,
) -> None:
    receipt = run_preflights(tmp_path / "evidence", "preflight-test")

    rows = {row["case"]: row for row in receipt["rows"]}
    assert receipt["observation_count"] == 6
    assert len({row["isolation_id"] for row in rows.values()}) == 6
    assert rows["selective_above_cap"]["current_hermes_red"] is False
    assert (
        rows["selective_above_cap"]["disposition"]
        == "EXISTING HERMES MECHANISM SUFFICIENT"
    )
    assert rows["isolation_unrelated"]["security_label"] == "POLICY_UNADJUDICATED"
    assert rows["isolation_unrelated"]["is_vulnerability"] is False
    assert (tmp_path / "evidence" / "preflight-test" / "receipt.json").is_file()
    verify(tmp_path / "evidence" / "preflight-test" / "receipt.json")
