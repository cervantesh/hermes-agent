"""Worst-case provider call accounting for the frozen Lane R protocol."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CallCap:
    task_specification_calls: int
    role_generation_calls: int
    extraction_calls: int
    primary_judge_calls: int
    reversal_judge_calls: int
    max_attempts_per_call: int

    @property
    def total_calls(self) -> int:
        return (
            self.task_specification_calls
            + self.role_generation_calls
            + self.extraction_calls
            + self.primary_judge_calls
            + self.reversal_judge_calls
        )

    @property
    def transport_attempt_cap(self) -> int:
        return self.total_calls * self.max_attempts_per_call


def calculate_call_cap(
    scored_tasks: int,
    pilot_tasks: int,
    max_role_messages: int,
    reversal_tasks: int,
    max_attempts_per_call: int = 3,
) -> CallCap:
    if min(scored_tasks, pilot_tasks, max_role_messages, reversal_tasks) < 0:
        raise ValueError("call-cap inputs cannot be negative")
    if max_attempts_per_call < 1:
        raise ValueError("max_attempts_per_call must be positive")
    all_runs = scored_tasks + pilot_tasks
    return CallCap(
        task_specification_calls=0,
        role_generation_calls=2 * all_runs * (1 + max_role_messages),
        extraction_calls=2 * all_runs,
        primary_judge_calls=all_runs,
        reversal_judge_calls=reversal_tasks,
        max_attempts_per_call=max_attempts_per_call,
    )
