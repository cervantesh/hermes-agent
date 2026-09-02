from __future__ import annotations

import json

from evals.shared_context_research.tasks import TASKS_BY_ID
from evals.shared_context_research_v3.runtime_v3 import durable_projection_v3


def test_durable_projection_is_read_by_a_fresh_process() -> None:
    task = TASKS_BY_ID["compact_release_map"]

    text, receipts, exact = durable_projection_v3(task)

    assert exact is True
    assert (
        json.loads(text.removeprefix("<handoff-json>").removesuffix("</handoff-json>"))
        == task.source
    )
    assert any(receipt.get("fresh_process_read") is True for receipt in receipts)
    assert any(
        receipt.get("hop") == "scratchpad_readback"
        and receipt.get("transport") == "sqlite_fresh_process"
        for receipt in receipts
    )
