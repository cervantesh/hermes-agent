from evals.issue_375_fidelity_research.schedule import build_schedule


def test_schedule_is_deterministic_balanced_and_blinded():
    ids = [f"task-{index:03}" for index in range(100)]

    first = build_schedule(ids, seed="frozen-schedule", reversal_count=20)
    second = build_schedule(ids, seed="frozen-schedule", reversal_count=20)

    assert first == second
    assert sum(row["generation_order"][0] == "original" for row in first) == 50
    assert sum(row["judge_order"][0] == "original" for row in first) == 50
    assert sum(row["order_reversal"] for row in first) == 20
    assert all(row["blind_labels"] == ["Assistant 1", "Assistant 2"] for row in first)


def test_schedule_rejects_duplicate_ids():
    try:
        build_schedule(["same", "same"], seed="frozen-schedule", reversal_count=1)
    except ValueError as exc:
        assert "distinct" in str(exc)
    else:
        raise AssertionError("duplicate task IDs were accepted")
