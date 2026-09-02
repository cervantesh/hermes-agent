"""Resume-safe runner for all prospectively declared V3 cohorts."""

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

from .analysis_v3 import adjudicate_v3
from .protocol_v3 import COHORTS, PROVIDER, TASKS, TARGET_REVISION, validate_protocol_v3
from .source_manifest_v3 import manifest_digest_v3, source_manifest_v3
from evals.shared_context_research.protocol_v2 import PREFLIGHT_ONLY
from evals.shared_context_research.sanitize_evidence_v2 import verify_sanitized_v2


ROOT = Path(__file__).resolve().parent
SEAL = ROOT / "PROTOCOL_SEAL_V3.json"
REMOTE_SEAL = ROOT / "REMOTE_SEAL_RECEIPT.json"
PREFLIGHT_PASS = ROOT / "PREFLIGHT_PASS_RECEIPT_V3.json"


def verify_seal_v3() -> dict[str, Any]:
    seal = json.loads(SEAL.read_text(encoding="utf-8"))
    if seal["target_revision"] != TARGET_REVISION:
        raise ValueError("seal target mismatch")
    manifest = source_manifest_v3(ROOT)
    if manifest != seal["source_manifest"]:
        raise ValueError("sealed V3 source changed")
    if manifest_digest_v3(manifest) != seal["source_manifest_sha256"]:
        raise ValueError("sealed V3 source digest mismatch")
    validate_protocol_v3()
    return seal


def verify_remote_seal_v3(seal: dict[str, Any]) -> dict[str, Any]:
    if not REMOTE_SEAL.is_file():
        raise ValueError("remote seal receipt missing")
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
        raise ValueError("remote seal receipt incomplete")
    if receipt["repository"] != "cervantesh/hermes-agent":
        raise ValueError("unexpected remote seal repository")
    if receipt["source_manifest_sha256"] != seal["source_manifest_sha256"]:
        raise ValueError("remote seal source digest mismatch")
    committed = datetime.fromisoformat(
        receipt["github_committed_at_utc"].replace("Z", "+00:00")
    ).astimezone(timezone.utc)
    if committed > datetime.now(timezone.utc):
        raise ValueError("remote seal timestamp is in the future")
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
            f"{source_commit}:evals/shared_context_research_v3/PROTOCOL_SEAL_V3.json",
        ],
        cwd=ROOT,
        text=True,
    )
    if json.loads(committed_seal) != seal:
        raise ValueError("remote source commit does not contain the active seal")
    for key, expected in seal["source_manifest"].items():
        namespace, name = key.split("/", 1)
        directory = (
            "shared_context_research_v3"
            if namespace == "v3"
            else "shared_context_research"
        )
        content = subprocess.check_output(
            [
                "git",
                "show",
                f"{source_commit}:evals/{directory}/{name}",
            ],
            cwd=ROOT,
        )
        if hashlib.sha256(content).hexdigest() != expected:
            raise ValueError(f"remote source content mismatch: {key}")
    return receipt


def verify_preflight_pass_v3(
    seal: dict[str, Any], remote: dict[str, Any], *, root: Path = ROOT
) -> dict[str, Any]:
    receipt_path = root / "PREFLIGHT_PASS_RECEIPT_V3.json"
    if not receipt_path.is_file():
        raise ValueError("passed V3 preflight receipt missing")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    expected = {
        "kind": "unscored_provider_topology_preflight",
        "target_revision": TARGET_REVISION,
        "cohort": COHORTS[0].id,
        "fixtures": list(PREFLIGHT_ONLY),
        "observation_count": len(PREFLIGHT_ONLY),
        "source_manifest_sha256": seal["source_manifest_sha256"],
        "remote_seal_source_commit": remote["source_commit"],
        "passed": True,
    }
    if any(receipt.get(key) != value for key, value in expected.items()):
        raise ValueError("passed V3 preflight receipt mismatch")
    label = receipt.get("evidence_label")
    digest = receipt.get("observations_sha256")
    if not isinstance(label, str) or not label or not isinstance(digest, str):
        raise ValueError("passed V3 preflight evidence binding missing")
    public = root / "evidence" / label
    public_receipt = public / "receipt.json"
    observations = public / "observations.jsonl"
    if not public_receipt.is_file() or not observations.is_file():
        raise ValueError("passed V3 preflight evidence missing")
    if json.loads(public_receipt.read_text(encoding="utf-8")) != receipt:
        raise ValueError("passed V3 preflight receipt copies differ")
    if hashlib.sha256(observations.read_bytes()).hexdigest() != digest:
        raise ValueError("passed V3 preflight observation digest mismatch")
    rows = [
        json.loads(line)
        for line in observations.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    verify_sanitized_v2(rows)
    if len(rows) != receipt["observation_count"]:
        raise ValueError("passed V3 preflight observation count mismatch")
    if {row.get("task") for row in rows} != set(PREFLIGHT_ONLY):
        raise ValueError("passed V3 preflight fixture set mismatch")
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
            and set(row.get("arms") or {}) == {"A", "B", "C"}
            and bool(integrity)
            and all(value is True for value in integrity.values())
            and started >= published
        )
        if not valid:
            raise ValueError("passed V3 preflight observation failed semantic gates")
    return receipt


def _load(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def _run_fixture(
    args, cohort, task: str, *, preflight: bool = False
) -> tuple[dict[str, Any], int]:
    command = [
        sys.executable,
        "-m",
        "evals.shared_context_research_v3.fixture_worker_v3",
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
    last: dict[str, Any] | None = None
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
        last = json.loads(lines[-1]) if lines and lines[-1].startswith("{") else None
        if run.returncode == 2 and attempt == 1:
            continue
        if run.returncode not in (0, 2) or last is None:
            raise RuntimeError(
                f"fixture failed {cohort.id}/{task}: "
                f"stdout={run.stdout[-2000:]} stderr={run.stderr[-2000:]}"
            )
        return last, attempt
    raise AssertionError("unreachable")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--python-executable", required=True)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    seal = verify_seal_v3()
    remote_seal = verify_remote_seal_v3(seal)
    verify_preflight_pass_v3(seal, remote_seal)
    output = ROOT / "results-private" / args.label / "raw-v3.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = _load(output)
    completed = {(row.get("cohort"), row.get("task")) for row in rows}
    with output.open("a", encoding="utf-8") as sink:
        for cohort in COHORTS:
            for task in TASKS:
                key = (cohort.id, task)
                if key in completed:
                    print(f"{cohort.id}/{task}: already recorded", flush=True)
                    continue
                if source_manifest_v3(ROOT) != seal["source_manifest"]:
                    raise RuntimeError("decision-critical V3 source changed during run")
                run_started_at = (
                    datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                )
                record, attempts = _run_fixture(args, cohort, task)
                record.update({
                    "cohort": cohort.id,
                    "model": cohort.model,
                    "provider": PROVIDER,
                    "attempts": attempts,
                    "protocol_sha256": seal["protocol_sha256"],
                    "source_manifest_sha256": seal["source_manifest_sha256"],
                    "remote_seal_source_commit": remote_seal["source_commit"],
                    "run_started_at_utc": run_started_at,
                })
                sink.write(json.dumps(record, ensure_ascii=False) + "\n")
                sink.flush()
                rows.append(record)
                completed.add(key)
                print(
                    f"{cohort.id}/{task}: "
                    + ", ".join(
                        f"{arm}:ok={data.get('ok')}/f={data.get('handoff_fidelity')}"
                        for arm, data in record.get("arms", {}).items()
                    ),
                    flush=True,
                )
    decision = adjudicate_v3(rows)
    print(json.dumps({"decision": decision, "raw": str(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
