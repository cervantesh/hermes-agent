from analysis import paired, summarize


def test_summary_keeps_false_success_separate_from_failure() -> None:
    result = summarize(
        [
            {"ok": True, "false_success": False, "api_calls": 2, "duration_seconds": 3},
            {"ok": False, "false_success": True, "api_calls": 4, "duration_seconds": 5},
        ]
    )
    assert result["verified"] == 1
    assert result["false_success"] == 1
    assert result["api_calls"] == 6


def test_paired_reports_direction_and_cost_ratios() -> None:
    baseline = [
        {"task": "a", "ok": True, "api_calls": 2, "duration_seconds": 4},
        {"task": "b", "ok": False, "api_calls": 3, "duration_seconds": 6},
    ]
    candidate = [
        {"task": "a", "ok": False, "false_success": True, "api_calls": 4, "duration_seconds": 8},
        {"task": "b", "ok": True, "api_calls": 6, "duration_seconds": 12},
    ]
    result = paired(baseline, candidate)
    assert result["discordance"] == {
        "baseline_only_success": 1,
        "candidate_only_success": 1,
    }
    assert result["aggregate_api_call_ratio"] == 2
    assert result["aggregate_latency_ratio"] == 2
