"""Run the two unscored V2 topology preflights and emit safe receipts."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from .protocol_v2 import MODEL, PROVIDER, TARGET_REVISION
from .provenance_v2 import source_manifest_digest_v2, source_manifest_v2
from .sanitize_evidence_v2 import write_packet_v2


EVAL_DIR = Path(__file__).resolve().parent
PREFLIGHT_FIXTURES = (
    ("preflight_detached_echo", 377),
    ("preflight_shared_echo", 377),
)


def _run_one(args: argparse.Namespace, task: str, seed: int) -> dict[str, object]:
    command = [
        sys.executable,
        "-m",
        "evals.shared_context_research.fixture_worker_v2",
        "--repo-root",
        str(Path(args.repo_root).resolve()),
        "--python-executable",
        str(Path(args.python_executable).resolve()),
        "--task",
        task,
        "--schedule-seed",
        str(seed),
        "--provider",
        args.provider,
        "--model",
        args.model,
        "--preflight",
    ]
    env = dict(os.environ)
    env.update({"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
    run = subprocess.run(
        command,
        cwd=EVAL_DIR.parents[1],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=3600,
    )
    lines = [line for line in run.stdout.splitlines() if line.strip()]
    record = json.loads(lines[-1]) if lines and lines[-1].startswith("{") else None
    if run.returncode or record is None:
        detail = record or {"stdout": run.stdout[-4000:], "stderr": run.stderr[-4000:]}
        raise RuntimeError(f"preflight failed for {task}@{seed}: {detail}")
    record.update({"provider": args.provider, "model": args.model, "attempts": 1})
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--python-executable", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--provider", default=PROVIDER)
    parser.add_argument("--model", default=MODEL)
    args = parser.parse_args()
    repo = Path(args.repo_root).resolve()
    head = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()
    dirty = bool(
        subprocess.check_output(
            ["git", "-C", str(repo), "status", "--porcelain"], text=True
        ).strip()
    )
    if head != TARGET_REVISION or dirty:
        raise SystemExit(f"target identity mismatch: head={head}, dirty={dirty}")
    source_manifest = source_manifest_v2(EVAL_DIR)
    source_digest = source_manifest_digest_v2(source_manifest)
    raw_path = EVAL_DIR / "results-private" / args.label / "raw-v2.jsonl"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    if raw_path.exists():
        raise SystemExit(f"refusing to overwrite private preflight: {raw_path}")
    records = [_run_one(args, task, seed) for task, seed in PREFLIGHT_FIXTURES]
    for record in records:
        record.update({
            "protocol_sha256": source_manifest["PROTOCOL_FREEZE_V2.md"],
            "source_manifest": source_manifest,
            "source_manifest_sha256": source_digest,
        })
    raw_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records),
        encoding="utf-8",
    )
    invalid = {
        str(record["task"]): {
            name: value
            for name, value in (record.get("integrity") or {}).items()
            if value is not True
        }
        for record in records
        if record.get("provider_failure")
        or not record.get("producer_admitted")
        or any(value is not True for value in (record.get("integrity") or {}).values())
    }
    if invalid:
        raise SystemExit(
            "unscored preflight did not satisfy integrity gates; "
            f"private raw evidence retained: {json.dumps(invalid, sort_keys=True)}"
        )
    if source_manifest_v2(EVAL_DIR) != source_manifest:
        raise SystemExit("decision-critical source changed during preflight")
    public_dir = EVAL_DIR / "evidence" / args.label
    meta = write_packet_v2(raw_path, public_dir, expanded=False)
    print(json.dumps({"receipt": meta, "evidence_dir": str(public_dir)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
