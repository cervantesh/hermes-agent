from pathlib import Path

from .audit_run002 import audit


ROOT = Path(__file__).resolve().parent


def test_run002_is_complete_but_cannot_authorize_implementation() -> None:
    result = audit(ROOT / "evidence" / "v7-repetition-001-20260903")

    assert result["observation_count"] == 23
    assert result["receipt_observation_count"] == 23
    assert result["all_rows_have_canonical_prompt_tokens"] is True
    assert result["all_d_rows_tool_free"] is True
    assert result["track1_control_artifact"] is True
    assert result["track2_confirmation"] == {
        "b_count": 4,
        "d_count": 4,
        "all_b_valid_failures": True,
        "all_d_valid_successes": True,
    }
    assert result["b_configured_kanban_only"] is True
    assert result["strong_baseline_tools_missing"] == ["read_file", "terminal"]
    assert result["track3_positive_controls_valid_and_exact"] is False
    assert result["overall_disposition"] == "INCONCLUSIVE_PROTOCOL_IMPLEMENTATION"
    assert result["implementation_authorized"] is False
