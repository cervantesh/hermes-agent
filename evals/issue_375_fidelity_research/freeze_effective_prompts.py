"""Freeze per-task provider system-prompt hashes without copying task text."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .manifest import resolve_manifest
from .protocol import initial_relay_message
from .sources import load_prompt_sources, render_role_prompts


FREEZE_ID = "IP375-FIDELITY-EXECUTION-R1-2026-09-03"
CAMEL_REVISION = "c402032a7f7cd27e196356fbcf413c521a8cb4ca"


def _sha(value: str | bytes) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _canonical(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def build_artifact(
    *,
    dataset_path: Path,
    manifest_path: Path,
    camel_repo: Path,
    supplement_tex: Path,
    freeze_id: str = FREEZE_ID,
) -> dict[str, object]:
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    tasks = resolve_manifest(dataset_path, manifest)
    sources = load_prompt_sources(camel_repo, CAMEL_REVISION, supplement_tex)
    records = []
    for task in tasks:
        arms = {}
        for arm in ("original", "ablated"):
            prompts = render_role_prompts(
                sources,
                arm,
                task["assistant_role"],
                task["user_role"],
                task["specified_task"],
            )
            arms[arm] = {
                "assistant_system_sha256": _sha(prompts.assistant),
                "user_system_sha256": _sha(prompts.user),
                "initial_relay_sha256": _sha(initial_relay_message(prompts.user)),
            }
        records.append({"id": task["id"], "arms": arms})
    return {
        "schema_version": 1,
        "freeze_id": freeze_id,
        "sample_manifest_sha256": _sha(manifest_bytes),
        "records": records,
        "dynamic_prompt_rule": (
            "Every generated inter-agent message is hashed in its private runtime receipt "
            "before the next provider request; its bytes cannot be known prospectively."
        ),
    }


def generate(
    *,
    dataset_path: Path,
    manifest_path: Path,
    camel_repo: Path,
    supplement_tex: Path,
    output_path: Path,
    freeze_id: str = FREEZE_ID,
) -> str:
    artifact = build_artifact(
        dataset_path=dataset_path,
        manifest_path=manifest_path,
        camel_repo=camel_repo,
        supplement_tex=supplement_tex,
        freeze_id=freeze_id,
    )
    data = _canonical(artifact)
    output_path.write_bytes(data)
    return _sha(data)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--camel-repo", type=Path, required=True)
    parser.add_argument("--supplement-tex", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--freeze-id", default=FREEZE_ID)
    args = parser.parse_args()
    digest = generate(
        dataset_path=args.dataset,
        manifest_path=args.manifest,
        camel_repo=args.camel_repo,
        supplement_tex=args.supplement_tex,
        output_path=args.output,
        freeze_id=args.freeze_id,
    )
    print(digest)


if __name__ == "__main__":
    main()
