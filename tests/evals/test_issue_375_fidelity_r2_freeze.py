import json

from evals.issue_375_fidelity_research.freeze_r2_pilot import generate
from evals.issue_375_fidelity_research.manifest import build_sample_manifest


def _row(record_id: str):
    return {
        "id": record_id,
        "original_task": f"original {record_id}",
        "specified_task": f"specified {record_id}",
        "role_1": "Programmer_RoleType.ASSISTANT",
        "role_2": "Filmmaker_RoleType.USER",
    }


def test_r2_pilot_freeze_is_disjoint_and_content_addressed(tmp_path):
    dataset = tmp_path / "dataset.json"
    dataset.write_text(
        json.dumps([_row(str(index)) for index in range(30)]), encoding="utf-8"
    )
    scored = build_sample_manifest(dataset, sample_size=5, seed="scored")
    scored_path = tmp_path / "scored.json"
    scored_path.write_text(json.dumps(scored), encoding="utf-8")

    seal = generate(
        output_dir=tmp_path / "frozen",
        dataset_path=dataset,
        scored_manifest_path=scored_path,
        pilot_size=20,
    )

    pilot = json.loads((tmp_path / "frozen" / "PILOT_R2_MANIFEST.json").read_text())
    schedule = json.loads((tmp_path / "frozen" / "PILOT_R2_SCHEDULE.json").read_text())
    scored_ids = {record["id"] for record in scored["records"]}
    pilot_ids = {record["id"] for record in pilot["records"]}
    assert scored_ids.isdisjoint(pilot_ids)
    assert len(pilot_ids) == 20
    assert len(schedule) == 20
    assert all(row["order_reversal"] is False for row in schedule)
    assert seal["observations_started"] is False
    assert set(seal["artifacts"]) == {
        "PILOT_R2_MANIFEST.json",
        "PILOT_R2_SCHEDULE.json",
    }
