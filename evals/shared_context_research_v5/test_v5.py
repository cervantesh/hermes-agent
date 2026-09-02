from __future__ import annotations

from evals.shared_context_research.shared_context import canonical_bytes

from .protocol_v5 import gate_passes
from .tasks_v5 import build_tasks_v5, consumer_operation_v5


def test_fixtures_straddle_cap_and_select_last_record() -> None:
    below, above = build_tasks_v5()
    assert len(canonical_bytes(below.source).decode()) < 4096
    assert len(canonical_bytes(above.source).decode()) > 4096
    for task in (below, above):
        assert task.consumer_local["select"] == [task.source["records"][-1]["id"]]
        assert task.expected == {"selected": [task.source["records"][-1]]}


def test_operation_does_not_reveal_expected_value() -> None:
    below, _ = build_tasks_v5()
    operation = consumer_operation_v5(below)
    assert below.expected["selected"][0]["opaque"] not in operation


def test_gate_requires_below_green_and_above_result_red() -> None:
    base = {
        "producer_checks": {"exact": True},
        "schema_safe": True,
        "arm": {"ok": True, "consumer_checks": {"result_exact": True}},
    }
    below = {"task": "cap_below_control", **base}
    above = {
        "task": "cap_above_tail_dependency",
        **base,
        "arm": {"ok": False, "consumer_checks": {"result_exact": False}},
    }
    assert gate_passes([below, above])
    assert not gate_passes([below, {**above, "arm": base["arm"]}])
