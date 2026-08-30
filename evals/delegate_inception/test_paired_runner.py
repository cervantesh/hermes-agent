"""Regression tests for paired, interleaved A/B scheduling."""

from evals.delegate_inception.paired_runner import build_schedule


def test_schedule_is_reproducible_complete_and_interleaves_arms():
    first = build_schedule(["one", "two"], reps=3, seed=375)
    second = build_schedule(["one", "two"], reps=3, seed=375)

    assert first == second
    assert len(first) == 12
    assert {(row.arm, row.task_id, row.rep) for row in first} == {
        (arm, task, rep)
        for arm in ("baseline", "candidate")
        for task in ("one", "two")
        for rep in range(1, 4)
    }
    assert {row.arm for row in first[:4]} == {"baseline", "candidate"}


def test_different_seed_changes_order_not_membership():
    first = build_schedule(["one", "two"], reps=2, seed=1)
    second = build_schedule(["one", "two"], reps=2, seed=2)

    assert first != second
    assert set(first) == set(second)
