"""Frozen constants for the V5 cap-discrimination experiment."""

TARGET_REVISION = "c7429f60cadb21482c1e3e34ccf4f1014d887de8"
PROVIDER = "claude-code"
GATE_COHORT = {"id": "haiku-s377", "model": "claude-haiku-4-5", "seed": 377}
CONFIRMATION_COHORTS = (
    {"id": "haiku-s378", "model": "claude-haiku-4-5", "seed": 378},
    {"id": "sonnet-s377", "model": "claude-sonnet-4-6", "seed": 377},
)
TASK_IDS = ("cap_below_control", "cap_above_tail_dependency")


def gate_passes(rows: list[dict]) -> bool:
    by_task = {row["task"]: row for row in rows}
    below = by_task["cap_below_control"]
    above = by_task["cap_above_tail_dependency"]
    return bool(
        below["arm"]
        and below["arm"]["ok"]
        and above["arm"]
        and not above["arm"]["ok"]
        and not above["arm"]["consumer_checks"]["result_exact"]
        and all(below["producer_checks"].values())
        and all(above["producer_checks"].values())
        and below["schema_safe"]
        and above["schema_safe"]
    )
