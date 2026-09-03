"""Generate deterministic, content-addressed Lane R inputs without provider calls."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .budget import calculate_call_cap
from .manifest import build_sample_manifest
from .schedule import build_schedule
from .sources import load_prompt_sources


FREEZE_ID = "IP375-FIDELITY-EXECUTION-R1-2026-09-03"
PARENT_SHA256 = "c8de22a6da211616c15d16a9c37520682e8f219b8052c74af30cb12f8c5204ef"
DATASET_SHA256 = "f8cfd147969ced5a61ba6df3507d6e14348ec5b300e94c1a05ec67d0266c0c12"
CAMEL_REVISION = "c402032a7f7cd27e196356fbcf413c521a8cb4ca"
SAMPLE_SEED = "IP375-FIDELITY-R1"
SCHEDULE_SEED = "IP375-FIDELITY-R1-SCHEDULE"


def _canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write(path: Path, value: Any) -> str:
    data = _canonical_bytes(value)
    path.write_bytes(data)
    return _sha256(data)


def generate(
    *,
    output_dir: Path,
    dataset_path: Path,
    camel_repo: Path,
    supplement_tex: Path,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_sample_manifest(
        dataset_path,
        sample_size=100,
        seed=SAMPLE_SEED,
    )
    if manifest["source_sha256"] != DATASET_SHA256:
        raise ValueError("AI Society dataset does not match the frozen LFS object")

    schedule = build_schedule(
        [record["id"] for record in manifest["records"]],
        seed=SCHEDULE_SEED,
        reversal_count=20,
    )
    sources = load_prompt_sources(camel_repo, CAMEL_REVISION, supplement_tex)
    source_receipt = {
        "schema_version": 1,
        "freeze_id": FREEZE_ID,
        "camel_revision": CAMEL_REVISION,
        "task_specification_identity": "PINNED_DATASET_OUTPUT",
        "prompt_sha256": sources.sha256,
    }
    call_cap = calculate_call_cap(100, 4, 40, 20)
    budget_receipt = {
        "schema_version": 1,
        "freeze_id": FREEZE_ID,
        "task_specification_calls": call_cap.task_specification_calls,
        "role_generation_calls": call_cap.role_generation_calls,
        "extraction_calls": call_cap.extraction_calls,
        "primary_judge_calls": call_cap.primary_judge_calls,
        "reversal_judge_calls": call_cap.reversal_judge_calls,
        "total_calls": call_cap.total_calls,
        "note": "Worst case includes the excluded four-task provider pilot and its scored-sample rerun.",
    }

    hashes = {
        "SAMPLE_MANIFEST.json": _write(output_dir / "SAMPLE_MANIFEST.json", manifest),
        "SCHEDULE.json": _write(output_dir / "SCHEDULE.json", schedule),
        "SOURCE_PROMPT_RECEIPT.json": _write(
            output_dir / "SOURCE_PROMPT_RECEIPT.json", source_receipt
        ),
        "CALL_CAP.json": _write(output_dir / "CALL_CAP.json", budget_receipt),
    }
    seal = {
        "schema_version": 1,
        "freeze_id": FREEZE_ID,
        "status": "FROZEN_INPUTS_NO_PROVIDER_OBSERVATIONS",
        "parent_freeze_sha256": PARENT_SHA256,
        "artifacts": hashes,
        "pilot_record_ids": [record["id"] for record in manifest["records"][:4]],
        "observations_started": False,
    }
    _write(output_dir / "FROZEN_INPUTS_SEAL.json", seal)
    return hashes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--camel-repo", type=Path, required=True)
    parser.add_argument("--supplement-tex", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    hashes = generate(
        output_dir=args.output_dir,
        dataset_path=args.dataset,
        camel_repo=args.camel_repo,
        supplement_tex=args.supplement_tex,
    )
    print(json.dumps(hashes, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
