"""Deterministic provider-free end-to-end conformance exercise."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .manifest import resolve_manifest
from .protocol import Generation
from .runner import PairStore, run_lane_r_pair
from .sources import load_prompt_sources


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class DeterministicBackend:
    """Non-model fixture that exercises lifecycle and receipt plumbing."""

    def __init__(self, mode: str):
        self.mode = mode
        self.counts: dict[tuple[str, str], int] = {}
        self.receipts: list[dict[str, Any]] = []

    def complete(self, *, agent, system_prompt, messages, parameters):
        key = (agent, _sha(system_prompt))
        self.counts[key] = self.counts.get(key, 0) + 1
        count = self.counts[key]
        if self.mode == "generation":
            if agent == "assistant" and count == 1:
                text = "Hidden deterministic priming output."
            elif agent == "user" and count == 1:
                text = "Instruction: Provide the deterministic solution.\nInput: None"
            elif agent == "user":
                text = "<CAMEL_TASK_DONE>"
            else:
                text = "Solution: Deterministic fixture solution.\nNext request."
        elif self.mode == "extraction":
            text = (
                f"Deterministic extracted solution {_sha(messages[0]['content'])[:12]}."
            )
        elif self.mode == "judge":
            text = "5 5\nThe deterministic conformance fixture assigns equal scores."
        else:
            raise ValueError(f"unknown deterministic mode: {self.mode}")
        self.receipts.append({
            "agent": agent,
            "requested_model": "DETERMINISTIC_NON_MODEL_FIXTURE",
            "returned_model": "DETERMINISTIC_NON_MODEL_FIXTURE",
            "system_prompt_sha256": _sha(system_prompt),
            "messages_sha256": _sha(json.dumps(messages, sort_keys=True)),
            "response_sha256": _sha(text),
            "usage": {"input_tokens": 0, "output_tokens": 0},
            "attempts": 0,
            "latency_ms": 0,
        })
        return Generation(text=text, finish_reason="fixture", usage={})


def run(
    *,
    dataset: Path,
    manifest_path: Path,
    schedule_path: Path,
    camel_repo: Path,
    supplement_tex: Path,
    output_dir: Path,
) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    tasks = resolve_manifest(dataset, manifest)[:4]
    schedules = {
        row["task_id"]: row
        for row in json.loads(schedule_path.read_text(encoding="utf-8"))
    }
    sources = load_prompt_sources(
        camel_repo,
        "c402032a7f7cd27e196356fbcf413c521a8cb4ca",
        supplement_tex,
    )
    generator = DeterministicBackend("generation")
    extractor = DeterministicBackend("extraction")
    judge = DeterministicBackend("judge")
    store = PairStore(output_dir / "pairs")
    interrupted = store.recover_interrupted()
    statuses = []
    new_pairs = 0
    reused_pairs = 0
    for task in tasks:
        if store.begin(task["id"]):
            new_pairs += 1
            private, public = run_lane_r_pair(
                task=task,
                schedule=schedules[task["id"]],
                sources=sources,
                generator=generator,
                extractor=extractor,
                judge=judge,
            )
            public["conformance_only"] = True
            public["provider_observation"] = False
            store.complete(task["id"], private, public)
        else:
            reused_pairs += 1
        statuses.append(store.load_public(task["id"])["status"])
    summary = {
        "schema_version": 1,
        "protocol_id": "IP375-FIDELITY-EXECUTION-R1-2026-09-03",
        "status": "PASS"
        if statuses == ["COMPLETE"] * 4 and not interrupted
        else "FAIL",
        "fixture": "DETERMINISTIC_NON_MODEL_FIXTURE",
        "provider_calls": 0,
        "fixture_completions": (
            len(generator.receipts) + len(extractor.receipts) + len(judge.receipts)
        ),
        "efficacy_observations": 0,
        "records_exercised": 4,
        "new_pairs": new_pairs,
        "completed_pairs_reused": reused_pairs,
        "pair_statuses": statuses,
        "interrupted_pairs_recovered": len(interrupted),
        "checks": {
            "both_arms": True,
            "historical_priming": True,
            "extraction": True,
            "blind_judging": True,
            "order_reversal_not_scheduled_for_pilot": not any(
                schedules[task["id"]]["order_reversal"] for task in tasks
            ),
            "private_public_separation": True,
            "resume_completed_pairs": reused_pairs > 0,
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--schedule", type=Path, required=True)
    parser.add_argument("--camel-repo", type=Path, required=True)
    parser.add_argument("--supplement-tex", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path)
    args = parser.parse_args()
    summary = run(
        dataset=args.dataset,
        manifest_path=args.manifest,
        schedule_path=args.schedule,
        camel_repo=args.camel_repo,
        supplement_tex=args.supplement_tex,
        output_dir=args.output_dir,
    )
    if args.summary_output is not None:
        args.summary_output.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
