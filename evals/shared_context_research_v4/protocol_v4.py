"""V4 keeps the V3 experiment and changes only failure retention."""

from evals.shared_context_research_v3.protocol_v3 import (  # noqa: F401
    ALLOWED_KANBAN_OPERATIONS,
    COHORTS,
    CONTROLS,
    DEPENDENT,
    PROVIDER,
    TARGET_REVISION,
    TASKS,
    Cohort,
    validate_protocol_v3,
)


def validate_protocol_v4() -> None:
    validate_protocol_v3()
