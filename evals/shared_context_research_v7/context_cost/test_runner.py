from __future__ import annotations

import json
import pytest

from ..common.harness import OpaqueCorpus
from ..common.model_runtime import Cohort, ModelResult
from .runner import run_case


def test_runner_gives_b_real_show_and_d_only_declared_projection() -> None:
    prompts: dict[str, tuple[str, tuple[str, ...]]] = {}
    corpus = OpaqueCorpus.generate(seed=377, record_count=32, value_bytes=48)
    requested = (corpus.keys[3], corpus.keys[27])
    expected = json.dumps(
        {"selected": {key: corpus.records[key] for key in requested}},
        sort_keys=True,
        separators=(",", ":"),
    )

    def fake_model(**kwargs) -> ModelResult:
        message = kwargs["user_message"]
        arm = "B" if "Call kanban_show" in message else "D"
        prompts[arm] = (message, tuple(kwargs["enabled_toolsets"]))
        return ModelResult(
            final_response=expected,
            input_tokens=1000 if arm == "B" else 700,
            output_tokens=20,
            cache_read_tokens=0,
            latency_ms=100 if arm == "B" else 70,
            api_calls=1,
            tool_counts={"kanban_show": 1} if arm == "B" else {},
        )

    cohort = Cohort("test", "openai-codex", "gpt-5.4", "codex_responses")
    rows = run_case(
        cohort=cohort,
        seed=377,
        record_count=32,
        value_bytes=48,
        requested_indexes=(3, 27),
        model_call=fake_model,
    )

    assert {row["arm"] for row in rows} == {"B", "D"}
    assert all(row["external_oracle"] for row in rows)
    assert prompts["B"][1] == ("kanban",)
    assert "Call kanban_show" in prompts["B"][0]
    assert prompts["D"][1] == ()
    assert "DECLARED_JSON=" in prompts["D"][0]
    assert "EXPECTED_JSON=" not in prompts["B"][0]
    assert "EXPECTED_JSON=" not in prompts["D"][0]
    declared = prompts["D"][0].split("DECLARED_JSON=", 1)[1].splitlines()[0]
    assert len(json.loads(declared)) == 2


def test_runner_can_execute_only_the_prespecified_gate_arm() -> None:
    def fake_model(**kwargs) -> ModelResult:
        return ModelResult(
            final_response="{}",
            input_tokens=1,
            output_tokens=1,
            cache_read_tokens=0,
            latency_ms=1,
            api_calls=1,
            tool_counts={},
        )

    cohort = Cohort("test", "openai-codex", "gpt-5.4", "codex_responses")
    rows = run_case(
        cohort=cohort,
        seed=1,
        record_count=4,
        value_bytes=8,
        requested_indexes=(3,),
        arms=("B",),
        model_call=fake_model,
    )
    assert [row["arm"] for row in rows] == ["B"]

    with pytest.raises(ValueError, match="subset"):
        run_case(
            cohort=cohort,
            seed=1,
            record_count=4,
            value_bytes=8,
            requested_indexes=(3,),
            arms=("A",),
            model_call=fake_model,
        )
