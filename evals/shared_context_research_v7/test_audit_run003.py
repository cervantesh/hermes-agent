from pathlib import Path

from .audit_run003 import audit


ROOT = Path(__file__).resolve().parent


def test_run003_closes_the_remaining_frozen_product_gates() -> None:
    result = audit(ROOT / "evidence" / "v7-repetition-002-20260903")

    assert result["observation_count"] == 7
    assert result["receipt_observation_count"] == 7
    assert result["aborted"] is False
    assert result["all_rows_have_canonical_prompt_tokens"] is True
    assert result["strong_baseline_contract"] == {
        "configured_toolsets": [("hermes-cli",)],
        "required_tools_resolve": True,
        "largest_case_used_spill_recovery": True,
    }
    assert result["track2"]["record_counts"] == [32, 128, 512]
    assert result["track2"]["all_valid_and_exact"] is True
    assert result["track2"]["confirmation_count"] == 0
    assert result["track3"]["positive_controls_valid_and_exact"] is True
    assert result["track3"]["unrelated_rows_valid_and_visible"] is True
    assert result["track3"]["all_rows_have_durable_current_worker_outcome"] is True
    assert result["track3"]["policy_status"] == "POLICY_UNADJUDICATED"
    assert result["track3"]["is_vulnerability"] is False
    assert (
        result["overall_disposition"]
        == "NO_IMPLEMENTATION_JUSTIFIED_BY_FROZEN_EVIDENCE"
    )
    assert result["implementation_authorized"] is False
