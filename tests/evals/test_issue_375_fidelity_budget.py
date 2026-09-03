from evals.issue_375_fidelity_research.budget import calculate_call_cap


def test_call_cap_includes_excluded_pilot_rerun_and_order_reversal():
    cap = calculate_call_cap(
        scored_tasks=100,
        pilot_tasks=4,
        max_role_messages=40,
        reversal_tasks=20,
    )

    assert cap.role_generation_calls == 2 * (100 + 4) * (1 + 40)
    assert cap.extraction_calls == 2 * (100 + 4)
    assert cap.primary_judge_calls == 100 + 4
    assert cap.reversal_judge_calls == 20
    assert cap.total_calls == 8_860
    assert cap.max_attempts_per_call == 3
    assert cap.transport_attempt_cap == 26_580


def test_task_specification_adds_no_provider_calls():
    cap = calculate_call_cap(100, 4, 40, 20)

    assert cap.task_specification_calls == 0
