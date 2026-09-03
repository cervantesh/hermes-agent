from .common.evidence import verify_seal
from .repetition2.credentialed_execution import ROOT


def test_run003_audit_seal_matches_final_evidence() -> None:
    verify_seal(ROOT, ROOT / "RUN_003_AUDIT_SEAL.json")
