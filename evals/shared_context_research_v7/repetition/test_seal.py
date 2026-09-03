from ..common.evidence import verify_seal
from .credentialed_execution import ROOT


def test_corrected_repetition_seal_matches_active_bytes() -> None:
    verify_seal(ROOT, ROOT / "REPETITION_PROTOCOL_SEAL.json")
