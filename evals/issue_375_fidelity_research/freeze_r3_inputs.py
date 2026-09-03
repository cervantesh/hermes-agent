"""Freeze the fresh, fully reversed R3 judge-calibration cohort."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .manifest import build_sample_manifest
from .schedule import build_schedule


PROTOCOL_ID = "IP375-JUDGE-CALIBRATION-R3-2026-09-03"
PROTOCOL_SHA256 = "ab70597ea1515dfb8460fd157578d329c384cb92c99bf1fc5b818cbafb2e18de"
SAMPLE_SEED = "IP375-JUDGE-CALIBRATION-R3"
SCHEDULE_SEED = "IP375-JUDGE-CALIBRATION-R3-SCHEDULE"


def _canonical(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write(path: Path, value: Any) -> str:
    data = _canonical(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return _sha(data)


def _ids(path: Path) -> set[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "records" in payload:
        return {str(record["id"]) for record in payload["records"]}
    if "pilot_record_ids" in payload:
        return {str(task_id) for task_id in payload["pilot_record_ids"]}
    raise ValueError(f"exclusion manifest {path.name} contains no recognized IDs")


def generate(
    *,
    output_dir: Path,
    dataset_path: Path,
    exclusion_manifests: list[Path],
    prompt_artifacts: list[Path] | None = None,
) -> dict[str, Any]:
    exclusions: set[str] = set()
    exclusion_hashes = {}
    for path in exclusion_manifests:
        data = path.read_bytes()
        exclusion_hashes[path.name] = _sha(data)
        exclusions.update(_ids(path))
    manifest = build_sample_manifest(
        dataset_path,
        sample_size=30,
        seed=SAMPLE_SEED,
        exclude_ids=exclusions,
    )
    task_ids = [str(record["id"]) for record in manifest["records"]]
    if exclusions.intersection(task_ids):
        raise ValueError("R3 cohort overlaps an excluded research frame")
    schedule = build_schedule(
        task_ids,
        seed=SCHEDULE_SEED,
        reversal_count=len(task_ids),
    )
    artifacts = {
        "R3_MANIFEST.json": _write(output_dir / "R3_MANIFEST.json", manifest),
        "R3_SCHEDULE.json": _write(output_dir / "R3_SCHEDULE.json", schedule),
    }
    seal = {
        "schema_version": 1,
        "protocol_id": PROTOCOL_ID,
        "protocol_sha256": PROTOCOL_SHA256,
        "status": "FROZEN_INPUTS_NO_PROVIDER_OBSERVATIONS",
        "sample_size": len(task_ids),
        "sample_seed": SAMPLE_SEED,
        "schedule_seed": SCHEDULE_SEED,
        "excluded_id_count": len(exclusions),
        "excluded_ids_sha256": manifest["excluded_ids_sha256"],
        "exclusion_manifest_sha256": exclusion_hashes,
        "prompt_artifact_sha256": {
            path.name: _sha(path.read_bytes()) for path in (prompt_artifacts or [])
        },
        "artifacts": artifacts,
        "observations_started": False,
    }
    _write(output_dir / "R3_INPUTS_SEAL.json", seal)
    return seal


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--exclude", type=Path, action="append", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--prompt-artifact", type=Path, action="append", default=[])
    args = parser.parse_args()
    print(
        json.dumps(
            generate(
                output_dir=args.output_dir,
                dataset_path=args.dataset,
                exclusion_manifests=args.exclude,
                prompt_artifacts=args.prompt_artifact,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
