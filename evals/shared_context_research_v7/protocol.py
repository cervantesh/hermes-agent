"""Prospectively frozen V7 cohorts, fixtures, thresholds, and stopping rules."""

from __future__ import annotations

from .common.model_runtime import Cohort


FREEZE_ID = "SCR-V7-INITIAL-2026-09-02"
HERMES_REVISION = "593aa74c6182ce2e5e23bc102daaaae71710c05d"
CAMEL_REVISION = "5cd0d0f4bda29893bdbf90c707c4ee59e36c829c"

COHORTS = (
    Cohort(
        id="anthropic-sonnet46",
        provider="anthropic",
        model="claude-sonnet-4-6",
        api_mode="anthropic_messages",
    ),
    Cohort(
        id="openai-codex-gpt54",
        provider="openai-codex",
        model="gpt-5.4",
        api_mode="codex_responses",
    ),
)

TRACK1_CASES = (
    {
        "id": "subset",
        "seed": 377,
        "record_count": 80,
        "value_bytes": 96,
        "requested_indexes": (7, 73),
    },
    {
        "id": "all_records_control",
        "seed": 378,
        "record_count": 12,
        "value_bytes": 32,
        "requested_indexes": tuple(range(12)),
    },
)

TRACK2_GATE_COHORT = COHORTS[0]
TRACK2_GATE_SEED = 377
TRACK2_CONFIRMATION_SEEDS = (377, 378)
TRACK3_SEED = 91
TRACK3_RELATIONSHIPS = (
    "declared_completed_parent",
    "unrelated_same_board",
)

TOKEN_REDUCTION_GATE = 0.15
LATENCY_REDUCTION_GATE = 0.20
