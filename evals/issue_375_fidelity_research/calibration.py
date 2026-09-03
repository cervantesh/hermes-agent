"""Crash-safe, efficacy-blind judge calibration for protocol R3."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from .protocol import CompletionBackend, run_role_play
from .runner import (
    JudgeOutputFormatError,
    JudgeScoreRangeError,
    _completion,
    _receipts_since,
    _transcript_text,
    parse_judge_scores,
)
from .sources import PromptSources, render_role_prompts


def _canonical(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _safe_component(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ValueError("track and order names must be safe path components")
    return value


def _unmapped_numeric_pair(text: str) -> list[float] | None:
    first_line = text.splitlines()[0].strip() if text.splitlines() else ""
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)", first_line)
    return [float(value) for value in match.groups()] if match else None


def _mapped_outcome(answer_order: list[str], scores: tuple[float, float]) -> str:
    mapped = {answer_order[0]: scores[0], answer_order[1]: scores[1]}
    if mapped["original"] > mapped["ablated"]:
        return "original"
    if mapped["ablated"] > mapped["original"]:
        return "ablated"
    return "draw"


class CalibrationStore:
    """Persist judge request ownership, raw output, and sanitized final receipts."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.private = self.root / "private"
        self.public = self.root / "public"
        self.in_progress = self.root / "in_progress"
        self.fixture_private = self.root / "fixtures" / "private"
        self.fixture_public = self.root / "fixtures" / "public"
        self.fixture_in_progress = self.root / "fixtures" / "in_progress"
        for path in (
            self.private,
            self.public,
            self.in_progress,
            self.fixture_private,
            self.fixture_public,
            self.fixture_in_progress,
        ):
            path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _key(task_id: str) -> str:
        return hashlib.sha256(task_id.encode("utf-8")).hexdigest()

    def _path(self, base: Path, task_id: str, track: str, order: str) -> Path:
        directory = base / _safe_component(track) / _safe_component(order)
        directory.mkdir(parents=True, exist_ok=True)
        return directory / f"{self._key(task_id)}.json"

    @staticmethod
    def _atomic_write(path: Path, value: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        with temporary.open("wb") as target:
            target.write(_canonical(value))
            target.flush()
            os.fsync(target.fileno())
        temporary.replace(path)

    def begin_judgment(self, task_id: str, track: str, order: str) -> bool:
        if self._path(self.public, task_id, track, order).is_file():
            return False
        marker = self._path(self.in_progress, task_id, track, order)
        try:
            with marker.open("x", encoding="utf-8") as target:
                json.dump(
                    {"task_id": task_id, "track": track, "order": order},
                    target,
                    sort_keys=True,
                )
                target.flush()
                os.fsync(target.fileno())
        except FileExistsError:
            return False
        return True

    def persist_raw_judgment(
        self,
        *,
        task_id: str,
        track: str,
        order: str,
        answer_order: list[str],
        raw_response: str,
        transport_receipts: list[dict[str, Any]],
    ) -> None:
        if set(answer_order) != {"original", "ablated"} or len(answer_order) != 2:
            raise ValueError("answer order must contain both frozen arms")
        marker = self._path(self.in_progress, task_id, track, order)
        if not marker.is_file():
            raise RuntimeError(
                "raw judgment cannot be stored without request ownership"
            )
        self._atomic_write(
            self._path(self.private, task_id, track, order),
            {
                "schema_version": 1,
                "task_id": task_id,
                "track": track,
                "order": order,
                "status": "RAW_RESPONSE_PERSISTED",
                "answer_order": answer_order,
                "raw_response": raw_response,
                "transport_receipts": transport_receipts,
            },
        )

    def load_judgment_private(
        self, task_id: str, track: str, order: str
    ) -> dict[str, Any]:
        return json.loads(
            self._path(self.private, task_id, track, order).read_text(encoding="utf-8")
        )

    def load_judgment_public(
        self, task_id: str, track: str, order: str
    ) -> dict[str, Any]:
        return json.loads(
            self._path(self.public, task_id, track, order).read_text(encoding="utf-8")
        )

    def has_public(self, task_id: str, track: str, order: str) -> bool:
        return self._path(self.public, task_id, track, order).is_file()

    def has_raw_pending(self, task_id: str, track: str, order: str) -> bool:
        path = self._path(self.private, task_id, track, order)
        if not path.is_file():
            return False
        return json.loads(path.read_text(encoding="utf-8")).get("status") == (
            "RAW_RESPONSE_PERSISTED"
        )

    def finish_judgment(
        self,
        *,
        task_id: str,
        track: str,
        order: str,
        private: dict[str, Any],
        public: dict[str, Any],
    ) -> None:
        self._atomic_write(self._path(self.private, task_id, track, order), private)
        self._atomic_write(self._path(self.public, task_id, track, order), public)
        self._path(self.in_progress, task_id, track, order).unlink(missing_ok=True)

    def recover_interrupted_judgments(self) -> list[dict[str, str]]:
        recovered = []
        for marker in sorted(self.in_progress.glob("*/*/*.json")):
            ownership = json.loads(marker.read_text(encoding="utf-8"))
            task_id = ownership["task_id"]
            track = ownership["track"]
            order = ownership["order"]
            if self.has_raw_pending(task_id, track, order):
                continue
            receipt = {
                "task_id": task_id,
                "track": track,
                "order": order,
                "status": "QUARANTINED_UNKNOWN_PROVIDER_OUTCOME",
            }
            self.finish_judgment(
                task_id=task_id,
                track=track,
                order=order,
                private={"schema_version": 1, **receipt},
                public={"schema_version": 1, **receipt},
            )
            recovered.append(receipt)
        return recovered

    def _fixture_path(self, base: Path, task_id: str) -> Path:
        return base / f"{self._key(task_id)}.json"

    def begin_fixture(self, task_id: str) -> bool:
        if self._fixture_path(self.fixture_public, task_id).is_file():
            return False
        marker = self._fixture_path(self.fixture_in_progress, task_id)
        try:
            with marker.open("x", encoding="utf-8") as target:
                json.dump({"task_id": task_id}, target, sort_keys=True)
                target.flush()
                os.fsync(target.fileno())
        except FileExistsError:
            return False
        return True

    def load_fixture_private(self, task_id: str) -> dict[str, Any]:
        return json.loads(
            self._fixture_path(self.fixture_private, task_id).read_text(
                encoding="utf-8"
            )
        )

    def load_fixture_public(self, task_id: str) -> dict[str, Any]:
        return json.loads(
            self._fixture_path(self.fixture_public, task_id).read_text(encoding="utf-8")
        )

    def has_fixture(self, task_id: str) -> bool:
        return self._fixture_path(self.fixture_public, task_id).is_file()

    def finish_fixture(
        self,
        *,
        task_id: str,
        private: dict[str, Any],
        public: dict[str, Any],
    ) -> None:
        self._atomic_write(self._fixture_path(self.fixture_private, task_id), private)
        self._atomic_write(self._fixture_path(self.fixture_public, task_id), public)
        self._fixture_path(self.fixture_in_progress, task_id).unlink(missing_ok=True)

    def recover_interrupted_fixtures(self) -> list[dict[str, str]]:
        recovered = []
        for marker in sorted(self.fixture_in_progress.glob("*.json")):
            task_id = json.loads(marker.read_text(encoding="utf-8"))["task_id"]
            receipt = {
                "task_id": task_id,
                "status": "QUARANTINED_UNKNOWN_PROVIDER_OUTCOME",
            }
            self.finish_fixture(
                task_id=task_id,
                private={"schema_version": 1, **receipt},
                public={"schema_version": 1, **receipt},
            )
            recovered.append(receipt)
        return recovered


def prepare_and_checkpoint_fixture(
    *,
    store: CalibrationStore,
    task: dict[str, str],
    schedule: dict[str, Any],
    sources: PromptSources,
    generator: CompletionBackend,
    extractor: CompletionBackend,
) -> dict[str, Any]:
    """Generate both arms and persist their extracted solutions before judging."""
    task_id = task["id"]
    if schedule["task_id"] != task_id:
        raise ValueError("task and schedule IDs differ")
    if store.has_fixture(task_id):
        return store.load_fixture_public(task_id)
    if not store.begin_fixture(task_id):
        raise RuntimeError("fixture is already owned without a recoverable result")

    arms: dict[str, dict[str, Any]] = {}
    solutions: dict[str, str] = {}
    phase = "generation"
    arm: str | None = None
    active_backend = generator
    receipt_start = len(getattr(active_backend, "receipts", []))
    try:
        for arm in schedule["generation_order"]:
            prompts = render_role_prompts(
                sources,
                arm,
                task["assistant_role"],
                task["user_role"],
                task["specified_task"],
            )
            phase = "generation"
            active_backend = generator
            receipt_start = len(getattr(active_backend, "receipts", []))
            role_play = run_role_play(prompts, generator, max_role_messages=40)
            transcript = _transcript_text(role_play.transcript)
            arms[arm] = {
                "transcript": transcript,
                "termination_reason": role_play.termination_reason,
                "num_role_messages": role_play.num_role_messages,
                "generation_receipts": _receipts_since(generator, receipt_start),
            }

        for arm in schedule["generation_order"]:
            phase = "extraction"
            active_backend = extractor
            receipt_start = len(getattr(active_backend, "receipts", []))
            solutions[arm] = _completion(
                extractor,
                agent="extractor",
                system_prompt=sources.solution_extraction,
                user_prompt=arms[arm]["transcript"],
                max_tokens=4096,
            )
            arms[arm]["extraction_receipts"] = _receipts_since(extractor, receipt_start)
    except Exception as error:
        transport_receipts = _sanitize_transport(
            _receipts_since(active_backend, receipt_start)
        )
        receipt = {
            "schema_version": 1,
            "task_id": task_id,
            "status": "QUARANTINED_FIXTURE_FAILURE",
            "cause_type": type(error).__name__,
            "phase": phase,
            "arm": arm,
            "transport_receipts": transport_receipts,
        }
        store.finish_fixture(
            task_id=task_id,
            private={**receipt, "error": str(error)},
            public=receipt,
        )
        return receipt

    private = {
        "schema_version": 1,
        "task_id": task_id,
        "status": "JUDGE_READY",
        "task": task,
        "schedule": schedule,
        "arms": arms,
        "solutions": solutions,
    }
    public = {
        "schema_version": 1,
        "task_id": task_id,
        "status": "JUDGE_READY",
        "specified_task_sha256": _sha(task["specified_task"]),
        "arms": {
            arm: {
                "transcript_sha256": _sha(data["transcript"]),
                "transcript_length": len(data["transcript"]),
                "solution_sha256": _sha(solutions[arm]),
                "solution_length": len(solutions[arm]),
                "termination_reason": data["termination_reason"],
                "num_role_messages": data["num_role_messages"],
                "generation_receipts": _sanitize_transport(data["generation_receipts"]),
                "extraction_receipts": _sanitize_transport(data["extraction_receipts"]),
            }
            for arm, data in arms.items()
        },
    }
    store.finish_fixture(task_id=task_id, private=private, public=public)
    return public


def _sanitize_transport(receipts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    allowed = {
        "requested_model",
        "returned_model",
        "response_sha256",
        "finish_reason",
        "usage",
        "attempts",
        "latency_ms",
        "content_types",
    }
    return [
        {key: value for key, value in receipt.items() if key in allowed}
        for receipt in receipts
    ]


def _finalize_raw(store: CalibrationStore, raw: dict[str, Any]) -> dict[str, Any]:
    task_id = raw["task_id"]
    track = raw["track"]
    order = raw["order"]
    text = raw["raw_response"]
    base_public = {
        "schema_version": 1,
        "task_id": task_id,
        "track": track,
        "order": order,
        "response_sha256": _sha(text),
        "response_length": len(text),
        "transport_receipts": _sanitize_transport(raw["transport_receipts"]),
    }
    private = dict(raw)
    try:
        scores = parse_judge_scores(text)
    except JudgeOutputFormatError:
        private.update({
            "status": "QUARANTINED_JUDGE_OUTPUT_FORMAT",
            "parse_category": "JudgeOutputFormatError",
        })
        public = {
            **base_public,
            "status": private["status"],
            "parse_category": private["parse_category"],
        }
    except JudgeScoreRangeError:
        private.update({
            "status": "QUARANTINED_JUDGE_SCORE_RANGE",
            "parse_category": "JudgeScoreRangeError",
            "unmapped_numeric_pair": _unmapped_numeric_pair(text),
        })
        public = {
            **base_public,
            "status": private["status"],
            "parse_category": private["parse_category"],
        }
    else:
        private.update({
            "status": "COMPLETE",
            "parse_category": "VALID",
            "unmapped_numeric_pair": list(scores),
            "mapped_outcome": _mapped_outcome(raw["answer_order"], scores),
        })
        public = {
            **base_public,
            "status": "COMPLETE",
            "parse_category": "VALID",
        }
    store.finish_judgment(
        task_id=task_id,
        track=track,
        order=order,
        private=private,
        public=public,
    )
    return public


def evaluate_judgment(
    *,
    store: CalibrationStore,
    task_id: str,
    track: str,
    order: str,
    answer_order: list[str],
    system_prompt: str,
    user_prompt: str,
    backend: CompletionBackend,
) -> dict[str, Any]:
    """Execute once, or finish a previously persisted raw response without a call."""
    if store.has_public(task_id, track, order):
        return store.load_judgment_public(task_id, track, order)
    if store.has_raw_pending(task_id, track, order):
        return _finalize_raw(store, store.load_judgment_private(task_id, track, order))
    if not store.begin_judgment(task_id, track, order):
        raise RuntimeError("judgment is already owned without a recoverable response")

    receipt_start = len(getattr(backend, "receipts", []))
    try:
        raw_response = _completion(
            backend,
            agent=f"judge_{track}_{order}",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=2048,
        )
    except Exception as error:
        receipt = {
            "schema_version": 1,
            "task_id": task_id,
            "track": track,
            "order": order,
            "status": "QUARANTINED_JUDGE_TRANSPORT_OR_IDENTITY",
            "cause_type": type(error).__name__,
        }
        store.finish_judgment(
            task_id=task_id,
            track=track,
            order=order,
            private={**receipt, "error": str(error)},
            public=receipt,
        )
        return receipt
    receipts = _receipts_since(backend, receipt_start)
    store.persist_raw_judgment(
        task_id=task_id,
        track=track,
        order=order,
        answer_order=answer_order,
        raw_response=raw_response,
        transport_receipts=receipts,
    )
    return _finalize_raw(store, store.load_judgment_private(task_id, track, order))


def summarize_calibration(
    *, store: CalibrationStore, task_ids: list[str], tracks: list[str]
) -> dict[str, Any]:
    """Return conformance counts only; never emit scores, winners, or arm totals."""
    track_summaries = {}
    for track in tracks:
        complete = 0
        invalid = 0
        identity_failures = 0
        reversal_pairs = 0
        reversal_agreements = 0
        for task_id in task_ids:
            judgments = {}
            for order in ("forward", "reverse"):
                if not store.has_public(task_id, track, order):
                    invalid += 1
                    continue
                public = store.load_judgment_public(task_id, track, order)
                if public["status"] == "COMPLETE":
                    complete += 1
                    judgments[order] = store.load_judgment_private(
                        task_id, track, order
                    )
                else:
                    invalid += 1
                    if public.get("cause_type") == "ModelIdentityError":
                        identity_failures += 1
            if set(judgments) == {"forward", "reverse"}:
                reversal_pairs += 1
                reversal_agreements += int(
                    judgments["forward"]["mapped_outcome"]
                    == judgments["reverse"]["mapped_outcome"]
                )
        track_summaries[track] = {
            "complete_judgments": complete,
            "invalid_judgments": invalid,
            "model_identity_failures": identity_failures,
            "reversal_agreements": reversal_agreements,
            "reversal_pairs": reversal_pairs,
        }
    return {
        "schema_version": 1,
        "protocol_id": "IP375-JUDGE-CALIBRATION-R3-2026-09-03",
        "task_count": len(task_ids),
        "efficacy_observations": 0,
        "eligible_for_pooling": False,
        "tracks": track_summaries,
    }
