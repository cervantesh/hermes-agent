"""Deterministic paired generation and blinded judging schedules."""

from __future__ import annotations

import hashlib


def _digest(seed: str, purpose: str, task_id: str) -> str:
    return hashlib.sha256(f"{seed}|{purpose}|{task_id}".encode()).hexdigest()


def _balanced_first_arm(task_ids: list[str], seed: str, purpose: str) -> set[str]:
    ordered = sorted(
        task_ids, key=lambda task_id: (_digest(seed, purpose, task_id), task_id)
    )
    return set(ordered[: len(ordered) // 2])


def build_schedule(
    task_ids: list[str], *, seed: str, reversal_count: int
) -> list[dict[str, object]]:
    if len(set(task_ids)) != len(task_ids):
        raise ValueError("task IDs must be distinct")
    if reversal_count < 0 or reversal_count > len(task_ids):
        raise ValueError("reversal_count must fit the task sample")

    original_generation_first = _balanced_first_arm(task_ids, seed, "generation")
    original_judge_first = _balanced_first_arm(task_ids, seed, "judge")
    reversal_ids = set(
        sorted(
            task_ids,
            key=lambda task_id: (_digest(seed, "reversal", task_id), task_id),
        )[:reversal_count]
    )
    rows = []
    for task_id in task_ids:
        generation_order = (
            ["original", "ablated"]
            if task_id in original_generation_first
            else ["ablated", "original"]
        )
        judge_order = (
            ["original", "ablated"]
            if task_id in original_judge_first
            else ["ablated", "original"]
        )
        rows.append({
            "task_id": task_id,
            "generation_order": generation_order,
            "judge_order": judge_order,
            "blind_labels": ["Assistant 1", "Assistant 2"],
            "order_reversal": task_id in reversal_ids,
        })
    return rows
