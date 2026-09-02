"""Resume-safe V4 runner that retains every terminal fixture outcome."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

from evals.shared_context_research.protocol_v2 import PREFLIGHT_ONLY
from evals.shared_context_research.sanitize_evidence_v2 import verify_sanitized_v2
from evals.shared_context_research_v3.analysis_v3 import adjudicate_v3

from .protocol_v4 import COHORTS, PROVIDER, TARGET_REVISION, TASKS, validate_protocol_v4
from .source_manifest_v4 import manifest_digest_v4, source_manifest_v4


ROOT = Path(__file__).resolve().parent
SEAL = ROOT / "PROTOCOL_SEAL_V4.json"
REMOTE_SEAL = ROOT / "REMOTE_SEAL_RECEIPT.json"
PREFLIGHT_PASS = ROOT / "PREFLIGHT_PASS_RECEIPT_V4.json"


def verify_seal_v4() -> dict[str, Any]:
    seal = json.loads(SEAL.read_text(encoding="utf-8"))
    if seal["target_revision"] != TARGET_REVISION:
        raise ValueError("V4 seal target mismatch")
    manifest = source_manifest_v4(ROOT)
    if manifest != seal["source_manifest"]:
        raise ValueError("sealed V4 source changed")
    if manifest_digest_v4(manifest) != seal["source_manifest_sha256"]:
        raise ValueError("sealed V4 source digest mismatch")
    validate_protocol_v4()
    return seal


def verify_remote_seal_v4(seal: dict[str, Any]) -> dict[str, Any]:
    receipt = json.loads(REMOTE_SEAL.read_text(encoding="utf-8"))
    required = {
        "repository",
        "source_commit",
        "github_commit_url",
        "github_committed_at_utc",
        "verified_at_utc",
        "source_manifest_sha256",
    }
    if not required <= set(receipt):
        raise ValueError("V4 remote seal receipt incomplete")
    if receipt["repository"] != "cervantesh/hermes-agent":
        raise ValueError("unexpected V4 remote seal repository")
    if receipt["source_manifest_sha256"] != seal["source_manifest_sha256"]:
        raise ValueError("V4 remote source digest mismatch")
    committed = datetime.fromisoformat(
        receipt["github_committed_at_utc"].replace("Z", "+00:00")
    ).astimezone(timezone.utc)
    if committed > datetime.now(timezone.utc):
        raise ValueError("V4 remote seal timestamp is in the future")
    source_commit = receipt["source_commit"]
    subprocess.run(
        ["git", "cat-file", "-e", f"{source_commit}^{{commit}}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    committed_seal = subprocess.check_output(
        [
            "git",
            "show",
            f"{source_commit}:evals/shared_context_research_v4/PROTOCOL_SEAL_V4.json",
        ],
        cwd=ROOT,
        text=True,
    )
    if json.loads(committed_seal) != seal:
        raise ValueError("remote V4 source commit lacks the active seal")
    for key, expected in seal["source_manifest"].items():
        namespace, name = key.split("/", 1)
        directory = (
            f"shared_context_research_{namespace}"
            if namespace != "v2"
            else "shared_context_research"
        )
        content = subprocess.check_output(
            ["git", "show", f"{source_commit}:evals/{directory}/{name}"],
            cwd=ROOT,
        )
        if hashlib.sha256(content).hexdigest() != expected:
            raise ValueError(f"remote V4 source content mismatch: {key}")
    return receipt


def verify_preflight_pass_v4(
    seal: dict[str, Any], remote: dict[str, Any], *, root: Path = ROOT
) -> dict[str, Any]:
    receipt_path = root / "PREFLIGHT_PASS_RECEIPT_V4.json"
    if not receipt_path.is_file():
        raise ValueError("passed V4 preflight receipt missing")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    expected = {
        "kind": "unscored_provider_topology_preflight_v4",
        "target_revision": TARGET_REVISION,
        "cohort": COHORTS[0].id,
        "fixtures": list(PREFLIGHT_ONLY),
        "observation_count": len(PREFLIGHT_ONLY),
        "source_manifest_sha256": seal["source_manifest_sha256"],
        "remote_seal_source_commit": remote["source_commit"],
        "passed": True,
    }
    if any(receipt.get(key) != value for key, value in expected.items()):
        raise ValueError("passed V4 preflight receipt mismatch")
    label = receipt.get("evidence_label")
    public = root / "evidence" / str(label)
    public_receipt = public / "receipt.json"
    observations = public / "observations.jsonl"
    if not public_receipt.is_file() or not observations.is_file():
        raise ValueError("passed V4 preflight evidence missing")
    if json.loads(public_receipt.read_text(encoding="utf-8")) != receipt:
        raise ValueError("passed V4 preflight receipt copies differ")
    digest = hashlib.sha256(observations.read_bytes()).hexdigest()
    if digest != receipt.get("observations_sha256"):
        raise ValueError("passed V4 preflight observation digest mismatch")
    rows = [
        json.loads(line)
        for line in observations.read_text(encoding="utf-8").splitlines()
        if line
    ]
    verify_sanitized_v2(rows)
    if len(rows) != len(PREFLIGHT_ONLY) or {row.get("task") for row in rows} != set(
        PREFLIGHT_ONLY
    ):
        raise ValueError("passed V4 preflight fixture set mismatch")
    published = datetime.fromisoformat(
        remote["github_committed_at_utc"].replace("Z", "+00:00")
    ).astimezone(timezone.utc)
    for row in rows:
        started = datetime.fromisoformat(
            row["run_started_at_utc"].replace("Z", "+00:00")
        ).astimezone(timezone.utc)
        integrity = row.get("integrity") or {}
        valid = (
            row.get("preflight") is True
            and row.get("cohort") == COHORTS[0].id
            and row.get("model") == COHORTS[0].model
            and row.get("provider") == PROVIDER
            and row.get("target_head") == TARGET_REVISION
            and row.get("target_dirty") is False
            and row.get("source_manifest_sha256") == seal["source_manifest_sha256"]
            and row.get("remote_seal_source_commit") == remote["source_commit"]
            and row.get("producer_admitted") is True
            and not row.get("provider_failure")
            and not row.get("fixture_failure")
            and set(row.get("arms") or {}) == {"A", "B", "C"}
            and bool(integrity)
            and all(value is True for value in integrity.values())
            and started >= published
        )
        if not valid:
            raise ValueError("passed V4 preflight observation failed semantic gates")
    return receipt


def _load(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def _abort_path(output: Path) -> Path:
    return output.parent / "ABORTED.json"


def _inflight_path(output: Path) -> Path:
    return output.parent / "INFLIGHT.json"


def _refuse_aborted(output: Path) -> None:
    marker = _abort_path(output)
    if marker.is_file():
        raise RuntimeError(
            f"V4 label is permanently aborted; inspect {marker.name} and use a new protocol"
        )


def _record_inflight(
    output: Path, *, cohort: str, task: str, source_manifest_sha256: str
) -> None:
    marker = _inflight_path(output)
    payload = {
        "status": "inflight",
        "cohort": cohort,
        "task": task,
        "source_manifest_sha256": source_manifest_sha256,
        "started_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    temporary = marker.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(marker)


def _resolve_or_refuse_inflight(output: Path, rows: list[dict[str, Any]]) -> None:
    marker = _inflight_path(output)
    if not marker.is_file():
        return
    pending = json.loads(marker.read_text(encoding="utf-8"))
    key = (pending.get("cohort"), pending.get("task"))
    retained = {(row.get("cohort"), row.get("task")) for row in rows}
    if key in retained:
        marker.unlink()
        return
    raise RuntimeError("V4 label has an unresolved inflight slot and cannot be resumed")


def _record_protocol_abort(
    output: Path,
    *,
    cohort: str,
    task: str,
    source_manifest_sha256: str,
    exc: Exception,
) -> None:
    marker = _abort_path(output)
    marker.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "permanently_aborted",
        "cohort": cohort,
        "task": task,
        "exception_type": type(exc).__name__,
        "message_sha256": hashlib.sha256(str(exc).encode("utf-8")).hexdigest(),
        "source_manifest_sha256": source_manifest_sha256,
        "recorded_at_utc": datetime
        .now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
    }
    temporary = marker.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(marker)


def _run_fixture(
    args, cohort, task: str, *, preflight: bool = False
) -> tuple[dict[str, Any], int]:
    command = [
        sys.executable,
        "-m",
        "evals.shared_context_research_v4.fixture_worker_v4",
        "--repo-root",
        str(Path(args.repo_root).resolve()),
        "--python-executable",
        str(Path(args.python_executable).resolve()),
        "--task",
        task,
        "--schedule-seed",
        str(cohort.seed),
        "--provider",
        PROVIDER,
        "--model",
        cohort.model,
    ]
    if preflight:
        command.append("--preflight")
    env = dict(os.environ)
    env.update({"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
    for attempt in (1, 2):
        run = subprocess.run(
            command,
            cwd=ROOT.parents[1],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=3600,
        )
        lines = [line for line in run.stdout.splitlines() if line.strip()]
        record = json.loads(lines[-1]) if lines and lines[-1].startswith("{") else None
        if run.returncode == 2 and attempt == 1:
            continue
        if run.returncode not in (0, 2, 3) or record is None:
            raise RuntimeError(
                f"V4 worker protocol failure {cohort.id}/{task}: "
                f"stdout={run.stdout[-2000:]} stderr={run.stderr[-2000:]}"
            )
        return record, attempt
    raise AssertionError("unreachable")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--python-executable", required=True)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    seal = verify_seal_v4()
    remote = verify_remote_seal_v4(seal)
    verify_preflight_pass_v4(seal, remote)
    output = ROOT / "results-private" / args.label / "raw-v4.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    _refuse_aborted(output)
    rows = _load(output)
    _resolve_or_refuse_inflight(output, rows)
    completed = {(row.get("cohort"), row.get("task")) for row in rows}
    with output.open("a", encoding="utf-8") as sink:
        for cohort in COHORTS:
            for task in TASKS:
                key = (cohort.id, task)
                if key in completed:
                    print(f"{cohort.id}/{task}: already recorded", flush=True)
                    continue
                if source_manifest_v4(ROOT) != seal["source_manifest"]:
                    raise RuntimeError("decision-critical V4 source changed during run")
                started = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                _record_inflight(
                    output,
                    cohort=cohort.id,
                    task=task,
                    source_manifest_sha256=seal["source_manifest_sha256"],
                )
                try:
                    record, attempts = _run_fixture(args, cohort, task)
                except Exception as exc:
                    _record_protocol_abort(
                        output,
                        cohort=cohort.id,
                        task=task,
                        source_manifest_sha256=seal["source_manifest_sha256"],
                        exc=exc,
                    )
                    _inflight_path(output).unlink(missing_ok=True)
                    raise RuntimeError(
                        "V4 worker-protocol failure permanently aborted this label"
                    ) from exc
                record.update({
                    "cohort": cohort.id,
                    "model": cohort.model,
                    "provider": PROVIDER,
                    "attempts": attempts,
                    "protocol_sha256": seal["protocol_sha256"],
                    "source_manifest_sha256": seal["source_manifest_sha256"],
                    "remote_seal_source_commit": remote["source_commit"],
                    "run_started_at_utc": started,
                })
                sink.write(json.dumps(record, ensure_ascii=False) + "\n")
                sink.flush()
                os.fsync(sink.fileno())
                _inflight_path(output).unlink()
                rows.append(record)
                completed.add(key)
                status = (
                    "fixture_failure"
                    if record.get("fixture_failure")
                    else "provider_failure"
                    if record.get("provider_failure")
                    else "completed"
                )
                print(f"{cohort.id}/{task}: {status}", flush=True)
    print(
        json.dumps(
            {"decision": adjudicate_v3(rows), "raw": str(output)}, sort_keys=True
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
