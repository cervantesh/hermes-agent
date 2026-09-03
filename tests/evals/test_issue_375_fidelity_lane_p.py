import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).parents[2]
EVAL_DIR = ROOT / "evals" / "issue_375_fidelity_research"


def test_lane_p_opportunity_receipt_is_sealed_and_stops_without_observations():
    receipt = json.loads(
        (EVAL_DIR / "LANE_P_OPPORTUNITY_RECEIPT.json").read_text(encoding="utf-8")
    )
    audit_path = EVAL_DIR / receipt["canonical_artifact"]
    audit_bytes = audit_path.read_bytes()

    assert receipt["parent_freeze_id"] == "IP375-FIDELITY-INITIAL-2026-09-03"
    assert receipt["current_main"] == "25caae02c020f6dd7ecdc3eaf353ece85aeef09b"
    assert receipt["disposition"] == "NO_CURRENT_PRODUCT_OPPORTUNITY"
    assert receipt["provider_calls_made"] == 0
    assert receipt["efficacy_observations"] == 0
    assert receipt["treatment_freeze_created"] is False
    assert receipt["production_changes_made"] is False
    assert receipt["publications_made"] is False
    assert hashlib.sha256(audit_bytes).hexdigest() == receipt["sha256"]


def test_lane_p_audit_accounts_for_claimed_modes_and_current_owners():
    receipt = json.loads(
        (EVAL_DIR / "LANE_P_OPPORTUNITY_RECEIPT.json").read_text(encoding="utf-8")
    )
    modes = receipt["claimed_failure_modes"]
    candidates = {item["reference"]: item for item in receipt["candidate_cases"]}

    assert set(modes) == {
        "role_flipping",
        "instruction_echoing",
        "flake_replies",
        "infinite_loops",
    }
    assert all(not mode["eligible_red"] for mode in modes.values())
    assert candidates["#72901"]["classification"] == "fixed_different_cause"
    assert candidates["#79508"]["classification"] == "owned_active_pr"
    assert candidates["#16357"]["classification"] == "owned_structural_gap"
    assert candidates["#74604"]["classification"] == "owned_no_minimal_reproducer"
    assert candidates["#11171"]["classification"] == "owned_different_cause"
    assert candidates["#94858/#94956"]["classification"] == "owned_parent_loop"
    assert candidates["#17561"]["classification"] == "competing_treatment_no_red"
    assert candidates["#100223"]["classification"] == "closed_duplicate_treatment"


def test_lane_r_drift_receipt_proves_no_frozen_path_changed():
    receipt = json.loads(
        (EVAL_DIR / "LANE_R_MAIN_DRIFT_RECEIPT.json").read_text(encoding="utf-8")
    )

    assert receipt["from"] == "4dac5f28af54001b899c9b6fc8ba81cb58da2f0e"
    assert receipt["to"] == "25caae02c020f6dd7ecdc3eaf353ece85aeef09b"
    assert receipt["classification"] == "NO_IMPACT"
    assert receipt["commit_count"] == 9
    assert receipt["frozen_lane_r_paths_changed"] == []
    assert "tools/delegate_tool.py" not in receipt["changed_paths"]
