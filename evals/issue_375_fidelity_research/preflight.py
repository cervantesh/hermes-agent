"""Provider-free verification of the frozen Lane R execution frame."""

from __future__ import annotations

import argparse
import anthropic
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from .manifest import build_sample_manifest, resolve_manifest
from .schedule import build_schedule
from .sources import load_prompt_sources


EXPECTED = {
    "hermes_main": "4dac5f28af54001b899c9b6fc8ba81cb58da2f0e",
    "camel": "c402032a7f7cd27e196356fbcf413c521a8cb4ca",
    "dataset": "f8cfd147969ced5a61ba6df3507d6e14348ec5b300e94c1a05ec67d0266c0c12",
    "paper_pdf": "926c73c2ae9f9abc7612ab58373e428476f4de55db78646ed59de09810db7777",
    "paper_source": "232dc85336d51948808effa9590087b47ccdb7e4baa364b39120743da050faf2",
    "design": "c8de22a6da211616c15d16a9c37520682e8f219b8052c74af30cb12f8c5204ef",
    "protocol": "78294319621e91540173c2dc19b01eb3b698f70c735cbe7a44ea40b3a5310305",
}


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def _verify(path: Path, expected: str, checks: dict[str, bool], name: str) -> None:
    checks[name] = path.is_file() and _sha(path) == expected


def run_preflight(
    *,
    repo: Path,
    camel_repo: Path,
    dataset: Path,
    paper_pdf: Path,
    paper_source: Path,
    supplement_tex: Path,
) -> dict[str, Any]:
    root = repo / "evals" / "issue_375_fidelity_research"
    frozen = root / "frozen_inputs"
    checks: dict[str, bool] = {}

    _verify(
        root / "INITIAL_DESIGN_FREEZE.md", EXPECTED["design"], checks, "design_seal"
    )
    _verify(
        root / "EXECUTION_PROTOCOL_FREEZE.md",
        EXPECTED["protocol"],
        checks,
        "execution_protocol_seal",
    )
    _verify(dataset, EXPECTED["dataset"], checks, "dataset_sha256")
    _verify(paper_pdf, EXPECTED["paper_pdf"], checks, "paper_pdf_sha256")
    _verify(paper_source, EXPECTED["paper_source"], checks, "paper_source_sha256")

    origin_main = _git(repo, "rev-parse", "origin/main")
    checks["frozen_hermes_commit_available"] = (
        _git(repo, "rev-parse", f"{EXPECTED['hermes_main']}^{{commit}}")
        == EXPECTED["hermes_main"]
    )
    checks["camel_commit_available"] = (
        _git(camel_repo, "rev-parse", f"{EXPECTED['camel']}^{{commit}}")
        == EXPECTED["camel"]
    )

    active = json.loads((root / "ACTIVE_FREEZE.json").read_text(encoding="utf-8"))
    for amendment in active["amendments"]:
        seal = json.loads((root / amendment["seal"]).read_text(encoding="utf-8"))
        _verify(
            root / amendment["artifact"],
            seal["sha256"],
            checks,
            f"{amendment['amendment_id']}_seal",
        )

    frozen_seal = json.loads(
        (frozen / "FROZEN_INPUTS_SEAL.json").read_text(encoding="utf-8")
    )
    for name, digest in frozen_seal["artifacts"].items():
        _verify(frozen / name, digest, checks, f"frozen_{name}")
    effective_seal = json.loads(
        (frozen / "EFFECTIVE_SYSTEM_PROMPT_SEAL.json").read_text(encoding="utf-8")
    )
    _verify(
        frozen / effective_seal["artifact"],
        effective_seal["sha256"],
        checks,
        "effective_system_prompt_manifest",
    )

    stored_manifest_bytes = (frozen / "SAMPLE_MANIFEST.json").read_bytes()
    stored_manifest = json.loads(stored_manifest_bytes)
    regenerated_manifest = build_sample_manifest(
        dataset, sample_size=100, seed="IP375-FIDELITY-R1"
    )
    checks["sample_manifest_regenerates"] = (
        _canonical(regenerated_manifest) == stored_manifest_bytes
    )
    resolved = resolve_manifest(dataset, stored_manifest)
    stored_schedule = json.loads((frozen / "SCHEDULE.json").read_text(encoding="utf-8"))
    checks["schedule_regenerates"] = stored_schedule == build_schedule(
        [task["id"] for task in resolved],
        seed="IP375-FIDELITY-R1-SCHEDULE",
        reversal_count=20,
    )
    sources = load_prompt_sources(camel_repo, EXPECTED["camel"], supplement_tex)
    source_receipt = json.loads(
        (frozen / "SOURCE_PROMPT_RECEIPT.json").read_text(encoding="utf-8")
    )
    checks["source_prompt_hashes_regenerate"] = (
        sources.sha256 == source_receipt["prompt_sha256"]
    )

    observation_dir = root / "private_observations"
    checks["observation_ledger_empty"] = not observation_dir.exists() or not any(
        observation_dir.iterdir()
    )
    checks["anthropic_api_key_present"] = bool(os.environ.get("ANTHROPIC_API_KEY"))
    checks["explicit_run_authorization_present"] = (
        root / "RUN_AUTHORIZATION.json"
    ).is_file()
    checks["anthropic_runtime_version"] = anthropic.__version__ == "0.87.0"
    checks["anthropic_metadata_matches_runtime"] = (
        anthropic.__version__ == importlib.metadata.version("anthropic")
    )
    checks["tiktoken_runtime_version"] = (
        importlib.metadata.version("tiktoken") == "0.12.0"
    )
    checks["scipy_runtime_version"] = importlib.metadata.version("scipy") == "1.17.1"

    required = [name for name in checks if not name.endswith("_present")]
    evidence_valid = all(checks[name] for name in required)
    ready = (
        evidence_valid
        and checks["anthropic_api_key_present"]
        and checks["explicit_run_authorization_present"]
    )
    return {
        "schema_version": 1,
        "protocol_id": "IP375-FIDELITY-EXECUTION-R1-2026-09-03",
        "status": "READY" if ready else "BLOCKED_BEFORE_PROVIDER_CALLS",
        "checks": checks,
        "versions": {
            "python": ".".join(map(str, sys.version_info[:3])),
            "anthropic_runtime": anthropic.__version__,
            "anthropic_metadata": importlib.metadata.version("anthropic"),
            "anthropic_metadata_matches_runtime": (
                anthropic.__version__ == importlib.metadata.version("anthropic")
            ),
            "tiktoken": importlib.metadata.version("tiktoken"),
            "scipy": importlib.metadata.version("scipy"),
        },
        "configured_models": {
            "generation_and_extraction": "claude-haiku-4-5-20251001",
            "primary_judge": "claude-sonnet-4-5-20250929",
        },
        "source_revisions": {
            "frozen_hermes": EXPECTED["hermes_main"],
            "origin_main_at_preflight": origin_main,
            "paper_era_camel": EXPECTED["camel"],
        },
        "contains_paths_or_account_identity": False,
        "provider_calls_made": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--camel-repo", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--paper-pdf", type=Path, required=True)
    parser.add_argument("--paper-source", type=Path, required=True)
    parser.add_argument("--supplement-tex", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = run_preflight(
        repo=args.repo,
        camel_repo=args.camel_repo,
        dataset=args.dataset,
        paper_pdf=args.paper_pdf,
        paper_source=args.paper_source,
        supplement_tex=args.supplement_tex,
    )
    args.output.write_bytes(_canonical(receipt))
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
