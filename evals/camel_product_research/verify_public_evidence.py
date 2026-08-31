"""Verify the committed CAMEL research receipts and published aggregates.

Exit codes deliberately distinguish a disproved claim from an audit that could
not inspect its inputs:

* 0: every claim confirmed
* 1: at least one claim refuted
* 2: no claim refuted, but at least one claim was undetermined
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Any

from analysis import paired


class Verdict(str, Enum):
    CONFIRMED = "confirmed"
    REFUTED = "refuted"
    UNDETERMINED = "undetermined"


@dataclass(frozen=True)
class Claim:
    id: str
    claim: str
    check: str
    verdict: Verdict
    evidence: str


@dataclass(frozen=True)
class Report:
    claims: tuple[Claim, ...]

    @property
    def overall(self) -> Verdict:
        verdicts = {claim.verdict for claim in self.claims}
        if Verdict.REFUTED in verdicts:
            return Verdict.REFUTED
        if Verdict.UNDETERMINED in verdicts:
            return Verdict.UNDETERMINED
        return Verdict.CONFIRMED

    @property
    def exit_code(self) -> int:
        return {
            Verdict.CONFIRMED: 0,
            Verdict.REFUTED: 1,
            Verdict.UNDETERMINED: 2,
        }[self.overall]

    def by_id(self, claim_id: str) -> Claim:
        return next(claim for claim in self.claims if claim.id == claim_id)

    def render(self) -> str:
        def safe(value: str) -> str:
            return value.replace("|", "\\|").replace("\n", " ")

        lines = [
            "| Claim | Check | Verdict | Raw evidence |",
            "|---|---|---|---|",
        ]
        lines.extend(
            "| "
            + " | ".join((
                safe(claim.claim),
                safe(claim.check),
                claim.verdict.value.upper(),
                safe(claim.evidence),
            ))
            + " |"
            for claim in self.claims
        )
        lines.extend(("", f"OVERALL: {self.overall.value.upper()}"))
        return "\n".join(lines)


@dataclass(frozen=True)
class AggregateSpec:
    name: str
    baseline: str
    candidate: str
    tasks: frozenset[str]
    expected: dict[str, Any]


_RECEIPTS = (
    "haiku45-baseline.jsonl",
    "haiku45-camel-adaptation.jsonl",
    "sonnet46-baseline.jsonl",
    "sonnet46-camel-adaptation.jsonl",
)

_PRIVATE_FIELDS = frozenset({
    "repo",
    "camel_repo",
    "summary",
    "error",
    "tool_trace",
    "protocol.messages",
})

_AGGREGATES = (
    AggregateSpec(
        name="haiku",
        baseline="haiku45-baseline.jsonl",
        candidate="haiku45-camel-adaptation.jsonl",
        tasks=frozenset({
            "simple_manifest",
            "ambiguous_handoff",
            "false_success_shortcut",
        }),
        expected={
            "baseline": {"n": 3, "verified": 3, "false_success": 0},
            "candidate": {"n": 3, "verified": 1, "false_success": 2},
            "aggregate_api_call_ratio": 3.74,
            "aggregate_latency_ratio": 8.41,
            "discordance": {
                "baseline_only_success": 2,
                "candidate_only_success": 0,
            },
        },
    ),
    AggregateSpec(
        name="sonnet",
        baseline="sonnet46-baseline.jsonl",
        candidate="sonnet46-camel-adaptation.jsonl",
        tasks=frozenset({"simple_manifest", "false_success_shortcut"}),
        expected={
            "baseline": {"n": 2, "verified": 2, "false_success": 0},
            "candidate": {"n": 2, "verified": 2, "false_success": 0},
            "aggregate_api_call_ratio": 2.92,
            "aggregate_latency_ratio": 2.02,
            "discordance": {
                "baseline_only_success": 0,
                "candidate_only_success": 0,
            },
        },
    ),
)


def _contains_path(record: dict[str, Any], dotted_path: str) -> bool:
    current: Any = record
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]
    return True


def _receipt_claim(
    evidence_dir: Path, filename: str
) -> tuple[Claim, list[dict[str, Any]] | None]:
    receipt = evidence_dir / filename
    metadata_path = receipt.with_suffix(".meta.json")
    check = "SHA-256, LF bytes, row count, schema, and privacy exclusions"
    if not receipt.is_file() or not metadata_path.is_file():
        missing = [path.name for path in (receipt, metadata_path) if not path.is_file()]
        return (
            Claim(
                f"receipt:{filename}",
                f"{filename} is an intact public receipt",
                check,
                Verdict.REFUTED,
                f"missing: {', '.join(missing)}",
            ),
            None,
        )

    try:
        raw = receipt.read_bytes()
        metadata_raw = metadata_path.read_text(encoding="utf-8")
    except OSError as exc:
        return (
            Claim(
                f"receipt:{filename}",
                f"{filename} is an intact public receipt",
                check,
                Verdict.UNDETERMINED,
                f"could not read input: {type(exc).__name__}: {exc}",
            ),
            None,
        )

    problems: list[str] = []
    try:
        metadata = json.loads(metadata_raw)
    except (json.JSONDecodeError, TypeError) as exc:
        metadata = {}
        problems.append(f"invalid metadata JSON: {exc}")

    digest = hashlib.sha256(raw).hexdigest()
    expected_digest = metadata.get("evidence_sha256")
    if digest != expected_digest:
        problems.append(f"hash mismatch: expected {expected_digest}, got {digest}")
    if b"\r" in raw:
        problems.append("receipt contains CR bytes instead of canonical LF")
    if raw and not raw.endswith(b"\n"):
        problems.append("receipt lacks a final LF")

    records: list[dict[str, Any]] = []
    try:
        text = raw.decode("utf-8")
        records = [json.loads(line) for line in text.splitlines() if line.strip()]
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        problems.append(f"invalid UTF-8 JSONL: {exc}")

    expected_records = metadata.get("records")
    if len(records) != expected_records:
        problems.append(
            f"record count mismatch: expected {expected_records}, got {len(records)}"
        )

    excluded = set(metadata.get("excluded_sensitive_fields") or ())
    if not _PRIVATE_FIELDS.issubset(excluded):
        problems.append(
            "metadata omits privacy exclusions: "
            + ", ".join(sorted(_PRIVATE_FIELDS - excluded))
        )
    included = set(metadata.get("included_fields") or ())
    protocol_included = set(metadata.get("included_protocol_fields") or ())
    allowed_top = included | {"protocol"}
    for index, record in enumerate(records, start=1):
        top_fields = set(record)
        if top_fields != allowed_top:
            problems.append(
                f"row {index} top-level schema mismatch: "
                f"missing={sorted(allowed_top - top_fields)}, "
                f"extra={sorted(top_fields - allowed_top)}"
            )
        protocol = record.get("protocol")
        if protocol is not None and (
            not isinstance(protocol, dict) or set(protocol) != protocol_included
        ):
            actual = (
                sorted(protocol)
                if isinstance(protocol, dict)
                else type(protocol).__name__
            )
            problems.append(
                f"row {index} protocol schema mismatch: expected "
                f"{sorted(protocol_included)}, got {actual}"
            )
        leaked = sorted(
            field for field in _PRIVATE_FIELDS if _contains_path(record, field)
        )
        if leaked:
            problems.append(f"row {index} contains private fields: {', '.join(leaked)}")

    verdict = Verdict.REFUTED if problems else Verdict.CONFIRMED
    evidence = (
        "; ".join(problems)
        if problems
        else (
            f"{len(records)} rows; sha256={digest}; zero CR bytes; "
            "declared private fields absent"
        )
    )
    return (
        Claim(
            f"receipt:{filename}",
            f"{filename} is an intact public receipt",
            check,
            verdict,
            evidence,
        ),
        records,
    )


def _aggregate_view(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "baseline": {
            key: result["baseline"][key] for key in ("n", "verified", "false_success")
        },
        "candidate": {
            key: result["candidate"][key] for key in ("n", "verified", "false_success")
        },
        "aggregate_api_call_ratio": result["aggregate_api_call_ratio"],
        "aggregate_latency_ratio": result["aggregate_latency_ratio"],
        "discordance": result["discordance"],
    }


def _aggregate_claim(
    spec: AggregateSpec,
    receipt_claims: dict[str, Claim],
    records: dict[str, list[dict[str, Any]] | None],
) -> Claim:
    inputs = (spec.baseline, spec.candidate)
    if any(receipt_claims[name].verdict is not Verdict.CONFIRMED for name in inputs):
        return Claim(
            f"aggregate:{spec.name}",
            f"The published {spec.name.title()} aggregate reconstructs",
            "Run paired analysis over the frozen task subset",
            Verdict.UNDETERMINED,
            "input receipt not confirmed",
        )
    try:
        result = paired(
            records[spec.baseline] or [],
            records[spec.candidate] or [],
            tasks=set(spec.tasks),
        )
    except (KeyError, TypeError, ValueError) as exc:
        return Claim(
            f"aggregate:{spec.name}",
            f"The published {spec.name.title()} aggregate reconstructs",
            "Run paired analysis over the frozen task subset",
            Verdict.REFUTED,
            f"analysis rejected the receipts: {type(exc).__name__}: {exc}",
        )
    actual = _aggregate_view(result)
    verdict = Verdict.CONFIRMED if actual == spec.expected else Verdict.REFUTED
    evidence = (
        json.dumps(actual, sort_keys=True, separators=(",", ":"))
        if verdict is Verdict.CONFIRMED
        else "expected "
        + json.dumps(spec.expected, sort_keys=True, separators=(",", ":"))
        + "; got "
        + json.dumps(actual, sort_keys=True, separators=(",", ":"))
    )
    return Claim(
        f"aggregate:{spec.name}",
        f"The published {spec.name.title()} aggregate reconstructs",
        "Run paired analysis over the frozen task subset",
        verdict,
        evidence,
    )


def verify(evidence_dir: Path) -> Report:
    receipt_claims: dict[str, Claim] = {}
    records: dict[str, list[dict[str, Any]] | None] = {}
    claims: list[Claim] = []
    for filename in _RECEIPTS:
        claim, parsed = _receipt_claim(evidence_dir, filename)
        receipt_claims[filename] = claim
        records[filename] = parsed
        claims.append(claim)
    claims.extend(
        _aggregate_claim(spec, receipt_claims, records) for spec in _AGGREGATES
    )
    return Report(tuple(claims))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify public CAMEL research receipts and aggregates."
    )
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        default=Path(__file__).with_name("evidence"),
    )
    args = parser.parse_args()
    report = verify(args.evidence_dir)
    print(report.render())
    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
