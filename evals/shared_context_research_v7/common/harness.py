"""Deterministic, provider-neutral primitives for the V7 research tracks.

This module deliberately measures only facts the harness can observe. In
particular, it records serialized bytes but never estimates model tokens.
Provider token counts must be supplied by the provider receipt.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import random
import statistics
from typing import Iterable, Mapping, Optional


@dataclass(frozen=True)
class OpaqueCorpus:
    """A deterministic corpus whose requested keys are chosen downstream."""

    records: Mapping[str, str]

    @classmethod
    def generate(
        cls, *, seed: int, record_count: int, value_bytes: int
    ) -> "OpaqueCorpus":
        if record_count < 1:
            raise ValueError("record_count must be positive")
        if value_bytes < 1:
            raise ValueError("value_bytes must be positive")
        randomizer = random.Random(seed)
        alphabet = "0123456789abcdef"
        records = {
            f"key-{index:05d}": "".join(
                randomizer.choice(alphabet) for _ in range(value_bytes)
            )
            for index in range(record_count)
        }
        return cls(records=records)

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(self.records)


@dataclass(frozen=True)
class Projection:
    payload: Mapping[str, str]
    serialized: bytes

    @property
    def utf8_bytes(self) -> int:
        return len(self.serialized)


def _projection(records: Mapping[str, str]) -> Projection:
    serialized = json.dumps(
        records, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return Projection(payload=dict(records), serialized=serialized)


def project_full(corpus: OpaqueCorpus) -> Projection:
    return _projection(corpus.records)


def project_declared(corpus: OpaqueCorpus, requested_keys: Iterable[str]) -> Projection:
    keys = tuple(requested_keys)
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate requested key")
    missing = [key for key in keys if key not in corpus.records]
    if missing:
        raise KeyError(missing[0])
    return _projection({key: corpus.records[key] for key in keys})


def exact_subset_digest(
    payload: Mapping[str, str], requested_keys: Iterable[str]
) -> str:
    subset = {key: payload[key] for key in requested_keys}
    canonical = json.dumps(
        subset, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


class AccessDenied(PermissionError):
    pass


@dataclass(frozen=True)
class AccessPolicy:
    workflow_id: str
    tenant_id: str
    board_id: str
    requester_task: str
    declared_parent_tasks: frozenset[str]
    completed_tasks: frozenset[str]
    declared_keys: frozenset[str]

    def authorize(
        self,
        *,
        owner_task: str,
        workflow_id: str,
        tenant_id: str,
        board_id: str,
        key: str,
    ) -> None:
        expected = (
            ("workflow_id", self.workflow_id, workflow_id),
            ("tenant_id", self.tenant_id, tenant_id),
            ("board_id", self.board_id, board_id),
        )
        for field, wanted, actual in expected:
            if actual != wanted:
                raise AccessDenied(f"{field} boundary denied")
        if key not in self.declared_keys:
            raise AccessDenied("key boundary denied")
        if owner_task == self.requester_task:
            return
        if owner_task not in self.declared_parent_tasks:
            raise AccessDenied("owner_task is not a declared parent")
        if owner_task not in self.completed_tasks:
            raise AccessDenied("owner_task parent is not completed")


@dataclass(frozen=True)
class ResourceResult:
    cohort: str
    external_success_equal: bool
    baseline_tokens: int
    candidate_tokens: int
    baseline_latency_ms: float
    candidate_latency_ms: float


@dataclass(frozen=True)
class GateDecision:
    passed: bool
    token_reduction: float
    latency_reduction: float
    reason: str


def _reduction(baseline: float, candidate: float) -> float:
    if baseline <= 0:
        raise ValueError("baseline metric must be positive")
    return (baseline - candidate) / baseline


def resource_gate(results: Iterable[ResourceResult]) -> GateDecision:
    rows = tuple(results)
    cohorts = {row.cohort for row in rows}
    if len(cohorts) < 2:
        return GateDecision(False, 0.0, 0.0, "fewer than two model cohorts")
    if not rows or not all(row.external_success_equal for row in rows):
        return GateDecision(False, 0.0, 0.0, "external success differs")

    baseline_tokens = statistics.median(row.baseline_tokens for row in rows)
    candidate_tokens = statistics.median(row.candidate_tokens for row in rows)
    baseline_latency = statistics.median(row.baseline_latency_ms for row in rows)
    candidate_latency = statistics.median(row.candidate_latency_ms for row in rows)
    token_reduction = _reduction(baseline_tokens, candidate_tokens)
    latency_reduction = _reduction(baseline_latency, candidate_latency)

    token_path = token_reduction >= 0.15 and latency_reduction >= 0.0
    latency_path = latency_reduction >= 0.20 and token_reduction >= 0.0
    passed = token_path or latency_path
    reason = "frozen resource gate passed" if passed else "resource threshold not met"
    return GateDecision(passed, token_reduction, latency_reduction, reason)


@dataclass(frozen=True)
class Observation:
    track: str
    arm: str
    cohort: str
    seed: int
    external_oracle: Optional[bool]
    prompt_bytes: int
    input_tokens: Optional[int] = None
    token_source: Optional[str] = None

    def __post_init__(self) -> None:
        if self.external_oracle is None:
            raise ValueError("external oracle result is required")
        if self.input_tokens is not None and not self.token_source:
            raise ValueError("measured input tokens require a token source")
        if self.input_tokens is None and self.token_source is not None:
            raise ValueError("token source cannot exist without a token count")
