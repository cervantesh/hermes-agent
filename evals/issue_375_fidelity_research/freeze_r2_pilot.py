"""Freeze the disjoint, unscored R2 provider-pilot cohort."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .manifest import build_sample_manifest
from .schedule import build_schedule


PROTOCOL_ID = "IP375-FIDELITY-EXECUTION-R2-2026-09-03"
PROTOCOL_SHA256 = "bc5dadff484c9f6529fabe1e613624eb7acbb6847d77133dd1da4e12dfbe5373"
PILOT_SEED = "IP375-FIDELITY-R2-PILOT"
SCHEDULE_SEED = "IP375-FIDELITY-R2-PILOT-SCHEDULE"


def _canonical(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write(path: Path, value: Any) -> str:
    data = _canonical(value)
    path.write_bytes(data)
    return _sha(data)


def generate(
    *,
    output_dir: Path,
    dataset_path: Path,
    scored_manifest_path: Path,
    pilot_size: int = 20,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    scored_bytes = scored_manifest_path.read_bytes()
    scored = json.loads(scored_bytes)
    excluded_ids = {str(record["id"]) for record in scored["records"]}
    pilot = build_sample_manifest(
        dataset_path,
        sample_size=pilot_size,
        seed=PILOT_SEED,
        exclude_ids=excluded_ids,
    )
    pilot_ids = [str(record["id"]) for record in pilot["records"]]
    if excluded_ids.intersection(pilot_ids):
        raise ValueError("R2 pilot overlaps the scored sample")
    schedule = build_schedule(
        pilot_ids,
        seed=SCHEDULE_SEED,
        reversal_count=0,
    )
    artifacts = {
        "PILOT_R2_MANIFEST.json": _write(output_dir / "PILOT_R2_MANIFEST.json", pilot),
        "PILOT_R2_SCHEDULE.json": _write(
            output_dir / "PILOT_R2_SCHEDULE.json", schedule
        ),
    }
    seal = {
        "schema_version": 1,
        "protocol_id": PROTOCOL_ID,
        "protocol_sha256": PROTOCOL_SHA256,
        "status": "FROZEN_PROSPECTIVE_NO_R2_OBSERVATIONS",
        "sample_size": pilot_size,
        "sample_seed": PILOT_SEED,
        "schedule_seed": SCHEDULE_SEED,
        "scored_manifest_sha256": _sha(scored_bytes),
        "excluded_id_count": len(excluded_ids),
        "excluded_ids_sha256": pilot["excluded_ids_sha256"],
        "artifacts": artifacts,
        "observations_started": False,
    }
    _write(output_dir / "PILOT_R2_SEAL.json", seal)
    return seal


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--scored-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            generate(
                output_dir=args.output_dir,
                dataset_path=args.dataset,
                scored_manifest_path=args.scored_manifest,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
