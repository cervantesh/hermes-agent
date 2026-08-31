import pytest

from analysis import paired, summarize


def _record(task: str, strategy: str, **overrides) -> dict:
    item = {
        "task": task,
        "rep": 1,
        "strategy": strategy,
        "label": f"{strategy}-label",
        "provider": "claude-code",
        "model": "test-model",
        "schedule_seed": 375,
        "head": f"{strategy}-head",
        "tree_digest": f"{strategy}-head",
        "ok": True,
        "false_success": False,
        "api_calls": 1,
        "duration_seconds": 1,
    }
    item.update(overrides)
    return item


def test_summary_keeps_false_success_separate_from_failure() -> None:
    result = summarize([
        {"ok": True, "false_success": False, "api_calls": 2, "duration_seconds": 3},
        {"ok": False, "false_success": True, "api_calls": 4, "duration_seconds": 5},
    ])
    assert result["verified"] == 1
    assert result["false_success"] == 1
    assert result["api_calls"] == 6


def test_paired_reports_direction_and_cost_ratios() -> None:
    baseline = [
        _record("a", "baseline", ok=True, api_calls=2, duration_seconds=4),
        _record("b", "baseline", ok=False, api_calls=3, duration_seconds=6),
    ]
    candidate = [
        _record(
            "a",
            "camel",
            ok=False,
            false_success=True,
            api_calls=4,
            duration_seconds=8,
        ),
        _record("b", "camel", ok=True, api_calls=6, duration_seconds=12),
    ]
    result = paired(baseline, candidate)
    assert result["discordance"] == {
        "baseline_only_success": 1,
        "candidate_only_success": 1,
    }
    assert result["aggregate_api_call_ratio"] == 2
    assert result["aggregate_latency_ratio"] == 2


def test_paired_rejects_duplicate_pair_identity() -> None:
    baseline = [_record("a", "baseline"), _record("a", "baseline", ok=False)]
    with pytest.raises(ValueError, match="duplicate pair identity"):
        paired(baseline, [_record("a", "camel")])


def test_paired_rejects_mixed_cohort_identity() -> None:
    baseline = [
        _record("a", "baseline"),
        _record("b", "baseline", model="other-model"),
    ]
    with pytest.raises(ValueError, match="mixed model"):
        paired(baseline, [_record("a", "camel"), _record("b", "camel")])


def test_paired_rejects_missing_cohort_identity() -> None:
    baseline = _record("a", "baseline")
    del baseline["head"]
    with pytest.raises(ValueError, match="missing head"):
        paired([baseline], [_record("a", "camel")])


def test_paired_rejects_incomplete_or_cross_model_pairs() -> None:
    with pytest.raises(ValueError, match="incomplete"):
        paired(
            [_record("a", "baseline"), _record("b", "baseline")],
            [_record("a", "camel")],
        )
    with pytest.raises(ValueError, match="differ on model"):
        paired(
            [_record("a", "baseline")],
            [_record("a", "camel", model="other-model")],
        )


def test_paired_requires_explicit_subset_when_baseline_has_extra_tasks() -> None:
    baseline = [_record("a", "baseline"), _record("b", "baseline")]
    candidate = [_record("a", "camel", schedule_seed=376)]
    with pytest.raises(ValueError, match="incomplete"):
        paired(baseline, candidate)
    result = paired(baseline, candidate, tasks={"a"})
    assert [item["task"] for item in result["tasks"]] == ["a"]
    assert result["baseline_identity"]["schedule_seed"] == 375
    assert result["candidate_identity"]["schedule_seed"] == 376
