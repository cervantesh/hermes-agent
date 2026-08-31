from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

from verify_public_evidence import Verdict, verify


EVIDENCE = Path(__file__).with_name("evidence")


def _copy_evidence(tmp_path: Path) -> Path:
    target = tmp_path / "evidence"
    shutil.copytree(EVIDENCE, target)
    return target


def _rewrite_metadata_hash(receipt: Path) -> None:
    metadata_path = receipt.with_suffix(".meta.json")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["evidence_sha256"] = hashlib.sha256(receipt.read_bytes()).hexdigest()
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def test_published_evidence_is_confirmed() -> None:
    report = verify(EVIDENCE)

    assert report.overall is Verdict.CONFIRMED
    assert report.exit_code == 0
    assert all(claim.verdict is Verdict.CONFIRMED for claim in report.claims)
    assert "OVERALL: CONFIRMED" in report.render()


def test_receipt_hash_mismatch_is_refuted(tmp_path: Path) -> None:
    evidence = _copy_evidence(tmp_path)
    receipt = evidence / "haiku45-baseline.jsonl"
    receipt.write_bytes(receipt.read_bytes().replace(b"{", b"{ ", 1))

    report = verify(evidence)

    claim = report.by_id("receipt:haiku45-baseline.jsonl")
    assert claim.verdict is Verdict.REFUTED
    assert "hash mismatch" in claim.evidence
    assert report.overall is Verdict.REFUTED
    assert report.exit_code == 1


def test_missing_receipt_is_refuted(tmp_path: Path) -> None:
    evidence = _copy_evidence(tmp_path)
    (evidence / "sonnet46-camel-adaptation.jsonl").unlink()

    report = verify(evidence)

    claim = report.by_id("receipt:sonnet46-camel-adaptation.jsonl")
    assert claim.verdict is Verdict.REFUTED
    assert "missing" in claim.evidence


def test_permission_failure_is_undetermined(tmp_path: Path, monkeypatch) -> None:
    evidence = _copy_evidence(tmp_path)
    original = Path.read_bytes

    def denied(path: Path) -> bytes:
        if path.name == "haiku45-baseline.jsonl":
            raise PermissionError("denied by test")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", denied)
    report = verify(evidence)

    claim = report.by_id("receipt:haiku45-baseline.jsonl")
    assert claim.verdict is Verdict.UNDETERMINED
    assert report.overall is Verdict.UNDETERMINED
    assert report.exit_code == 2


def test_aggregate_drift_is_refuted_even_with_a_matching_receipt_hash(
    tmp_path: Path,
) -> None:
    evidence = _copy_evidence(tmp_path)
    receipt = evidence / "haiku45-camel-adaptation.jsonl"
    rows = [
        json.loads(line) for line in receipt.read_text(encoding="utf-8").splitlines()
    ]
    rows[0]["ok"] = True
    receipt.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )
    _rewrite_metadata_hash(receipt)

    report = verify(evidence)

    assert (
        report.by_id("receipt:haiku45-camel-adaptation.jsonl").verdict
        is Verdict.CONFIRMED
    )
    aggregate = report.by_id("aggregate:haiku")
    assert aggregate.verdict is Verdict.REFUTED
    assert "expected" in aggregate.evidence
