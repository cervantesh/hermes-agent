from __future__ import annotations

import json
from pathlib import Path

import pytest

from ..protocol import COHORTS
from .study import decide_track1, decide_track3, run_repetition


def _resource_rows(*, subset_d_tokens: int = 700, control_d_tokens: int = 1000):
    rows = []
    for cohort in COHORTS:
        for case, d_tokens in (
            ("subset", subset_d_tokens),
            ("all_records_control", control_d_tokens),
        ):
            for arm in ("B", "D"):
                rows.append({
                    "track": "context_cost",
                    "case": case,
                    "arm": arm,
                    "cohort": cohort.id,
                    "external_oracle": True,
                    "valid_observation": True,
                    "prompt_tokens": 1000 if arm == "B" else d_tokens,
                    "latency_ms": 100.0,
                })
    return rows


def test_track1_requires_each_family_and_rejects_control_artifact() -> None:
    passed = decide_track1(_resource_rows())
    assert passed["disposition"] == "IMPLEMENTATION OPPORTUNITY"
    assert set(passed["subset_by_cohort"]) == {cohort.id for cohort in COHORTS}

    artifact = decide_track1(_resource_rows(control_d_tokens=700))
    assert artifact["disposition"] == "INCONCLUSIVE"
    assert artifact["control_artifact"] is True

    rows = _resource_rows()
    next(
        row
        for row in rows
        if row["case"] == "subset"
        and row["cohort"] == COHORTS[1].id
        and row["arm"] == "D"
    )["prompt_tokens"] = 950
    assert decide_track1(rows)["disposition"] == "NO DEMONSTRATED INCREMENT"


def test_track3_does_not_emit_policy_conclusion_when_positive_control_fails() -> None:
    rows = []
    for cohort in COHORTS:
        rows.extend((
            {
                "cohort": cohort.id,
                "relationship": "declared_completed_parent",
                "external_oracle": False,
                "valid_observation": True,
            },
            {
                "cohort": cohort.id,
                "relationship": "unrelated_same_board",
                "external_oracle": True,
                "valid_observation": True,
            },
        ))
    assert decide_track3(rows)["disposition"] == "INCONCLUSIVE"


def _context_runner(**kwargs):
    return [
        {
            "track": "context_cost",
            "arm": arm,
            "cohort": kwargs["cohort"].id,
            "seed": kwargs["seed"],
            "external_oracle": True,
            "valid_observation": True,
            "prompt_tokens": 1000 if arm == "B" else 700,
            "latency_ms": 100.0,
            "protocol_violations": [],
        }
        for arm in kwargs.get("arms", ("B", "D"))
    ]


def _isolation_runner(**kwargs):
    return {
        "track": "isolation",
        "arm": "B",
        "cohort": kwargs["cohort"].id,
        "seed": kwargs["seed"],
        "relationship": kwargs["relationship"],
        "external_oracle": True,
        "valid_observation": True,
        "protocol_violations": [],
    }


def test_orchestrator_stops_at_15_and_keeps_conditional_tracks_closed(
    tmp_path: Path,
) -> None:
    def boundary_runner(**kwargs):
        return {
            "expanded": False,
            "first_red_record_count": None,
            "disposition": "EXISTING HERMES MECHANISM SUFFICIENT",
            "rows": [
                {
                    "track": "selective_access",
                    "case": "b_first_boundary",
                    "arm": "B",
                    "cohort": kwargs["cohort"].id,
                    "seed": kwargs["seed"],
                    "record_count": size,
                    "external_oracle": True,
                    "valid_observation": True,
                    "protocol_violations": [],
                }
                for size in (32, 128, 512)
            ],
        }

    receipt = run_repetition(
        evidence_root=tmp_path,
        label="stop",
        context_runner=_context_runner,
        boundary_runner=boundary_runner,
        isolation_runner=_isolation_runner,
    )
    assert receipt["observation_count"] == 15
    assert receipt["tracks"]["active_writes"]["executed"] is False
    assert receipt["tracks"]["concurrency"]["executed"] is False
    assert receipt["tracks"]["remote_backends"]["executed"] is False


def test_orchestrator_expands_to_exactly_23_after_valid_b_red(tmp_path: Path) -> None:
    def boundary_runner(**kwargs):
        return {
            "expanded": True,
            "confirmation_allowed": True,
            "first_red_record_count": 512,
            "disposition": "INCONCLUSIVE",
            "rows": [
                {
                    "track": "selective_access",
                    "case": "b_first_boundary",
                    "arm": "B",
                    "cohort": kwargs["cohort"].id,
                    "seed": kwargs["seed"],
                    "record_count": size,
                    "external_oracle": size < 512,
                    "valid_observation": True,
                    "protocol_violations": [],
                }
                for size in (32, 128, 512)
            ],
        }

    def confirmation_runner(**kwargs):
        if "arms" not in kwargs:
            return _context_runner(**kwargs)
        return [
            {
                "track": "selective_access",
                "arm": arm,
                "cohort": kwargs["cohort"].id,
                "seed": kwargs["seed"],
                "external_oracle": arm == "D",
                "valid_observation": True,
                "prompt_tokens": 1000,
                "latency_ms": 100.0,
                "protocol_violations": [],
            }
            for arm in kwargs["arms"]
        ]

    receipt = run_repetition(
        evidence_root=tmp_path,
        label="expanded",
        context_runner=confirmation_runner,
        boundary_runner=boundary_runner,
        isolation_runner=_isolation_runner,
    )
    assert receipt["observation_count"] == 23
    assert (
        receipt["tracks"]["selective_access"]["disposition"]
        == "IMPLEMENTATION OPPORTUNITY"
    )


def test_orchestrator_retains_failure_even_during_postprocessing(
    tmp_path: Path,
) -> None:
    def broken_boundary(**kwargs):
        return {"expanded": False, "rows": []}

    with pytest.raises(KeyError):
        run_repetition(
            evidence_root=tmp_path,
            label="aborted",
            context_runner=_context_runner,
            boundary_runner=broken_boundary,
            isolation_runner=_isolation_runner,
        )
    abort = json.loads((tmp_path / "aborted" / "ABORTED.json").read_text())
    assert abort["type"] == "KeyError"
    assert abort["retained_observations"] == 12
