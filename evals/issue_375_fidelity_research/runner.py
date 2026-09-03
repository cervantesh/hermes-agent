"""Paired Lane R execution, sanitized receipts, and crash-safe pair ownership."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from .protocol import CompletionBackend, run_role_play
from .sources import (
    PromptSources,
    render_evaluation_prompt,
    render_role_prompts,
)


class LaneRExecutionError(RuntimeError):
    def __init__(self, phase: str, arm: str | None, cause: Exception):
        super().__init__(f"{phase} failed: {type(cause).__name__}: {cause}")
        self.phase = phase
        self.arm = arm
        self.cause = cause


class JudgeOutputError(ValueError):
    """A non-retryable judge response that violates the frozen score contract."""


class JudgeOutputFormatError(JudgeOutputError):
    pass


class JudgeScoreRangeError(JudgeOutputError):
    pass


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _transcript_text(transcript: list[dict[str, str]]) -> str:
    labels = {"user": "AI User", "assistant": "AI Assistant"}
    return "\n\n".join(
        f"{labels[message['role']]}:\n{message['content']}" for message in transcript
    )


def _completion(
    backend: CompletionBackend,
    *,
    agent: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
) -> str:
    generation = backend.complete(
        agent=agent,
        system_prompt=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
        parameters={
            "temperature": 0.0,
            "top_p": 1.0,
            "n": 1,
            "stream": False,
            "presence_penalty": 0.0,
            "frequency_penalty": 0.0,
            "max_tokens": max_tokens,
        },
    )
    if generation.terminated or not generation.text.strip():
        raise ValueError(f"{agent} returned no usable text")
    return generation.text


def parse_judge_scores(text: str) -> tuple[float, float]:
    first_line = text.splitlines()[0].strip() if text.splitlines() else ""
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)", first_line)
    if not match:
        raise JudgeOutputFormatError(
            "judge first line must contain exactly two numeric scores"
        )
    scores = tuple(float(value) for value in match.groups())
    if any(value < 1 or value > 10 for value in scores):
        raise JudgeScoreRangeError("judge scores must be within [1, 10]")
    return scores  # type: ignore[return-value]


def _mapped_scores(order: list[str], scores: tuple[float, float]) -> dict[str, float]:
    return {order[0]: scores[0], order[1]: scores[1]}


def _outcome(scores: dict[str, float]) -> str:
    if scores["original"] > scores["ablated"]:
        return "original"
    if scores["ablated"] > scores["original"]:
        return "ablated"
    return "draw"


def _receipts_since(backend: CompletionBackend, start: int) -> list[dict[str, Any]]:
    receipts = getattr(backend, "receipts", [])
    return [dict(receipt) for receipt in receipts[start:]]


def run_lane_r_pair(
    *,
    task: dict[str, str],
    schedule: dict[str, Any],
    sources: PromptSources,
    generator: CompletionBackend,
    extractor: CompletionBackend,
    judge: CompletionBackend,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if schedule["task_id"] != task["id"]:
        raise ValueError("task and schedule IDs differ")

    arms: dict[str, dict[str, Any]] = {}
    for arm in schedule["generation_order"]:
        prompts = render_role_prompts(
            sources,
            arm,
            task["assistant_role"],
            task["user_role"],
            task["specified_task"],
        )
        receipt_start = len(getattr(generator, "receipts", []))
        try:
            role_play = run_role_play(prompts, generator, max_role_messages=40)
        except Exception as error:
            raise LaneRExecutionError("generation", arm, error) from error
        transcript = _transcript_text(role_play.transcript)
        arms[arm] = {
            "transcript": transcript,
            "termination_reason": role_play.termination_reason,
            "num_role_messages": role_play.num_role_messages,
            "generation_receipts": _receipts_since(generator, receipt_start),
        }

    solutions: dict[str, str] = {}
    extraction_receipts: dict[str, list[dict[str, Any]]] = {}
    for arm in schedule["generation_order"]:
        receipt_start = len(getattr(extractor, "receipts", []))
        try:
            solutions[arm] = _completion(
                extractor,
                agent="extractor",
                system_prompt=sources.solution_extraction,
                user_prompt=arms[arm]["transcript"],
                max_tokens=4096,
            )
        except Exception as error:
            raise LaneRExecutionError("extraction", arm, error) from error
        extraction_receipts[arm] = _receipts_since(extractor, receipt_start)

    judge_order = list(schedule["judge_order"])
    judge_prompt = render_evaluation_prompt(
        sources,
        task["specified_task"],
        solutions[judge_order[0]],
        solutions[judge_order[1]],
    )
    judge_start = len(getattr(judge, "receipts", []))
    try:
        judge_text = _completion(
            judge,
            agent="judge",
            system_prompt=sources.evaluation_system,
            user_prompt=judge_prompt,
            max_tokens=2048,
        )
        scores = _mapped_scores(judge_order, parse_judge_scores(judge_text))
    except Exception as error:
        raise LaneRExecutionError("judging", None, error) from error
    outcome = _outcome(scores)
    judge_receipts = _receipts_since(judge, judge_start)

    reversal: dict[str, Any] | None = None
    if schedule["order_reversal"]:
        reversed_order = list(reversed(judge_order))
        reversed_prompt = render_evaluation_prompt(
            sources,
            task["specified_task"],
            solutions[reversed_order[0]],
            solutions[reversed_order[1]],
        )
        reversal_start = len(getattr(judge, "receipts", []))
        try:
            reversal_text = _completion(
                judge,
                agent="judge_reversal",
                system_prompt=sources.evaluation_system,
                user_prompt=reversed_prompt,
                max_tokens=2048,
            )
            reversal_scores = _mapped_scores(
                reversed_order, parse_judge_scores(reversal_text)
            )
        except Exception as error:
            raise LaneRExecutionError("reversal_judging", None, error) from error
        reversal = {
            "order": reversed_order,
            "text": reversal_text,
            "scores": reversal_scores,
            "outcome": _outcome(reversal_scores),
            "disagrees": _outcome(reversal_scores) != outcome,
            "receipts": _receipts_since(judge, reversal_start),
        }

    private = {
        "schema_version": 1,
        "task_id": task["id"],
        "status": "COMPLETE",
        "task": task,
        "schedule": schedule,
        "arms": arms,
        "solutions": solutions,
        "extraction_receipts": extraction_receipts,
        "judge_text": judge_text,
        "judge_receipts": judge_receipts,
        "scores": scores,
        "outcome": outcome,
        "reversal": reversal,
    }
    public_arms = {
        arm: {
            "transcript_sha256": _sha(data["transcript"]),
            "transcript_length": len(data["transcript"]),
            "solution_sha256": _sha(solutions[arm]),
            "solution_length": len(solutions[arm]),
            "termination_reason": data["termination_reason"],
            "num_role_messages": data["num_role_messages"],
            "generation_receipts": data["generation_receipts"],
            "extraction_receipts": extraction_receipts[arm],
        }
        for arm, data in arms.items()
    }
    public = {
        "schema_version": 1,
        "task_id": task["id"],
        "status": "COMPLETE",
        "arms": public_arms,
        "judge_response_sha256": _sha(judge_text),
        "judge_response_length": len(judge_text),
        "judge_receipts": judge_receipts,
        "scores": scores,
        "outcome": outcome,
        "reversal": (
            None
            if reversal is None
            else {
                "scores": reversal["scores"],
                "outcome": reversal["outcome"],
                "disagrees": reversal["disagrees"],
                "response_sha256": _sha(reversal["text"]),
                "response_length": len(reversal["text"]),
                "receipts": reversal["receipts"],
            }
        ),
    }
    return private, public


class PairStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.private = self.root / "private"
        self.public = self.root / "public"
        self.in_progress = self.root / "in_progress"
        for path in (self.private, self.public, self.in_progress):
            path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _key(task_id: str) -> str:
        return hashlib.sha256(task_id.encode("utf-8")).hexdigest()

    def _path(self, directory: Path, task_id: str) -> Path:
        return directory / f"{self._key(task_id)}.json"

    def begin(self, task_id: str) -> bool:
        if self._path(self.public, task_id).exists():
            return False
        marker = self._path(self.in_progress, task_id)
        try:
            with marker.open("x", encoding="utf-8") as target:
                target.write(task_id)
                target.flush()
                os.fsync(target.fileno())
        except FileExistsError:
            return False
        return True

    def has_public(self, task_id: str) -> bool:
        return self._path(self.public, task_id).is_file()

    @staticmethod
    def _atomic_write(path: Path, value: object) -> None:
        temporary = path.with_suffix(".tmp")
        with temporary.open("wb") as target:
            target.write(_canonical(value))
            target.flush()
            os.fsync(target.fileno())
        temporary.replace(path)

    def complete(
        self,
        task_id: str,
        private_receipt: dict[str, Any],
        public_receipt: dict[str, Any],
    ) -> None:
        self._atomic_write(self._path(self.private, task_id), private_receipt)
        self._atomic_write(self._path(self.public, task_id), public_receipt)
        self._path(self.in_progress, task_id).unlink(missing_ok=True)

    def load_public(self, task_id: str) -> dict[str, Any]:
        return json.loads(self._path(self.public, task_id).read_text(encoding="utf-8"))

    def recover_interrupted(self) -> list[str]:
        recovered = []
        for marker in sorted(self.in_progress.glob("*.json")):
            task_id = marker.read_text(encoding="utf-8")
            receipt = {
                "schema_version": 1,
                "task_id": task_id,
                "status": "QUARANTINED_INTERRUPTED_PAIR",
            }
            self._atomic_write(self._path(self.private, task_id), receipt)
            self._atomic_write(self._path(self.public, task_id), receipt)
            marker.unlink()
            recovered.append(task_id)
        return recovered
