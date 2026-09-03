from pathlib import Path

import pytest

from ..protocol import COHORTS
from .study import run_repetition2


def _isolation(**kwargs):
    return {
        "track": "isolation",
        "arm": "B",
        "cohort": kwargs["cohort"].id,
        "seed": kwargs["seed"],
        "relationship": kwargs["relationship"],
        "external_oracle": True,
        "valid_observation": True,
        "protocol_violations": [],
        "configured_toolsets": ["kanban"],
    }


def test_stops_at_seven_when_strong_b_is_exact(tmp_path: Path) -> None:
    def boundary(**kwargs):
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
                    "configured_toolsets": ["hermes-cli"],
                }
                for size in (32, 128, 512)
            ],
        }

    receipt = run_repetition2(
        evidence_root=tmp_path,
        label="seven",
        boundary_runner=boundary,
        isolation_runner=_isolation,
    )

    assert receipt["observation_count"] == 7
    assert receipt["tracks"]["context_cost"]["repeated"] is False
    assert (
        receipt["tracks"]["selective_access"]["disposition"]
        == "EXISTING HERMES MECHANISM SUFFICIENT"
    )


def test_expands_to_fifteen_only_after_valid_red(tmp_path: Path) -> None:
    def boundary(**kwargs):
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
                    "configured_toolsets": ["hermes-cli"],
                }
                for size in (32, 128, 512)
            ],
        }

    def confirmation(**kwargs):
        return [
            {
                "track": "selective_access",
                "arm": arm,
                "cohort": kwargs["cohort"].id,
                "seed": kwargs["seed"],
                "external_oracle": arm == "D",
                "valid_observation": True,
                "protocol_violations": [],
                "configured_toolsets": ["hermes-cli"] if arm == "B" else [],
            }
            for arm in kwargs["arms"]
        ]

    receipt = run_repetition2(
        evidence_root=tmp_path,
        label="fifteen",
        context_runner=confirmation,
        boundary_runner=boundary,
        isolation_runner=_isolation,
    )

    assert receipt["observation_count"] == 15
    assert (
        receipt["tracks"]["selective_access"]["disposition"]
        == "IMPLEMENTATION OPPORTUNITY"
    )
    assert {
        row["cohort"] for row in receipt["rows"] if row.get("case") == "confirmation"
    } == {cohort.id for cohort in COHORTS}


def test_failure_retains_abort_receipt(tmp_path: Path) -> None:
    def broken_boundary(**kwargs):
        raise RuntimeError("synthetic boundary failure")

    with pytest.raises(RuntimeError, match="synthetic boundary failure"):
        run_repetition2(
            evidence_root=tmp_path,
            label="aborted",
            boundary_runner=broken_boundary,
        )

    aborted = tmp_path / "aborted" / "ABORTED.json"
    assert aborted.is_file()
    assert '"retained_observations": 0' in aborted.read_text(encoding="utf-8")
