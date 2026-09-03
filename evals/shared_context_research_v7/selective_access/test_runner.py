from __future__ import annotations

from ..common.model_runtime import Cohort, ModelResult
from .runner import run_b_boundary_gate


def test_boundary_gate_stops_without_d_when_current_hermes_stays_exact() -> None:
    calls = []

    def fake_case(**kwargs):
        calls.append(kwargs)
        return [
            {
                "arm": "B",
                "external_oracle": True,
                "record_count": kwargs["record_count"],
            }
        ]

    result = run_b_boundary_gate(
        cohort=Cohort("test", "openai-codex", "gpt-5.4", "codex_responses"),
        seed=377,
        model_call=lambda **kwargs: ModelResult(
            final_response="{}",
            input_tokens=1,
            output_tokens=1,
            cache_read_tokens=0,
            latency_ms=1,
            api_calls=1,
            tool_counts={},
        ),
        case_runner=fake_case,
    )

    assert result["expanded"] is False
    assert result["disposition"] == "EXISTING HERMES MECHANISM SUFFICIENT"
    assert len(calls) == 3
    assert all(call["arms"] == ("B",) for call in calls)


def test_boundary_gate_stops_at_first_real_red() -> None:
    def fake_case(**kwargs):
        exact = kwargs["record_count"] < 128
        return [{"arm": "B", "external_oracle": exact}]

    result = run_b_boundary_gate(
        cohort=Cohort("test", "openai-codex", "gpt-5.4", "codex_responses"),
        seed=377,
        model_call=lambda **kwargs: None,
        case_runner=fake_case,
    )

    assert result["expanded"] is True
    assert result["first_red_record_count"] == 128
    assert len(result["rows"]) == 2
