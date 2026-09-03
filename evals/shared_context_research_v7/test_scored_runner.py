from __future__ import annotations

from pathlib import Path

from .scored_runner import run_study, verify_target


def test_orchestrator_stops_track2_and_keeps_conditional_tracks_closed(
    tmp_path: Path,
) -> None:
    def context_runner(**kwargs):
        case = kwargs["record_count"]
        return [
            {
                "track": "context_cost",
                "arm": arm,
                "cohort": kwargs["cohort"].id,
                "seed": kwargs["seed"],
                "external_oracle": True,
                "input_tokens": 1000 if arm == "B" else 700,
                "latency_ms": 100,
                "case_marker": case,
            }
            for arm in ("B", "D")
        ]

    def boundary_runner(**kwargs):
        return {
            "expanded": False,
            "first_red_record_count": None,
            "disposition": "EXISTING HERMES MECHANISM SUFFICIENT",
            "rows": [
                {
                    "track": "selective_access",
                    "external_oracle": True,
                    "record_count": record_count,
                }
                for record_count in (32, 128, 512)
            ],
        }

    def isolation_runner(**kwargs):
        return {
            "track": "isolation",
            "external_oracle": True,
            "relationship": kwargs["relationship"],
            "security_label": (
                "POSITIVE_CONTROL"
                if kwargs["relationship"] == "declared_completed_parent"
                else "POLICY_UNADJUDICATED"
            ),
        }

    receipt = run_study(
        evidence_root=tmp_path,
        label="study",
        context_runner=context_runner,
        boundary_runner=boundary_runner,
        isolation_runner=isolation_runner,
        verify_protocol=False,
    )

    assert (
        receipt["tracks"]["context_cost"]["disposition"] == "IMPLEMENTATION OPPORTUNITY"
    )
    assert (
        receipt["tracks"]["context_cost"]["smaller_footprint_discriminant"] == "#95561"
    )
    assert (
        receipt["tracks"]["selective_access"]["disposition"]
        == "EXISTING HERMES MECHANISM SUFFICIENT"
    )
    assert receipt["tracks"]["active_writes"]["executed"] is False
    assert receipt["tracks"]["concurrency"]["executed"] is False
    assert receipt["tracks"]["remote_backends"]["executed"] is False
    assert receipt["observation_count"] == 15


def test_orchestrator_confirms_track2_red_across_both_families_and_seeds(
    tmp_path: Path,
) -> None:
    def context_runner(**kwargs):
        arms = kwargs.get("arms", ("B", "D"))
        track = "selective_access" if "arms" in kwargs else "context_cost"
        return [
            {
                "track": track,
                "arm": arm,
                "cohort": kwargs["cohort"].id,
                "seed": kwargs["seed"],
                "external_oracle": arm == "D",
                "input_tokens": 100,
                "latency_ms": 100,
            }
            for arm in arms
        ]

    def boundary_runner(**kwargs):
        return {
            "expanded": True,
            "first_red_record_count": 128,
            "disposition": "INCONCLUSIVE",
            "rows": [
                {
                    "track": "selective_access",
                    "external_oracle": record_count < 128,
                    "record_count": record_count,
                }
                for record_count in (32, 128, 512)
            ],
        }

    def isolation_runner(**kwargs):
        return {
            "track": "isolation",
            "external_oracle": True,
            "relationship": kwargs["relationship"],
            "security_label": "POSITIVE_CONTROL",
        }

    receipt = run_study(
        evidence_root=tmp_path,
        label="expanded",
        context_runner=context_runner,
        boundary_runner=boundary_runner,
        isolation_runner=isolation_runner,
        verify_protocol=False,
    )

    assert (
        receipt["tracks"]["selective_access"]["disposition"]
        == "IMPLEMENTATION OPPORTUNITY"
    )
    assert receipt["observation_count"] == 23


def test_target_verifier_accepts_current_clean_production_tree() -> None:
    verify_target(Path(__file__).resolve().parents[2])
