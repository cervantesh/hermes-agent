import json

from evals.issue_375_fidelity_research.freeze_r3_inputs import generate


def _write_dataset(path, count=170):
    records = [
        {
            "id": f"{index:03d}",
            "original_task": f"Original task {index}",
            "specified_task": f"Specified task {index}",
            "role_1": "Programmer_RoleType.ASSISTANT",
            "role_2": "Filmmaker_RoleType.USER",
        }
        for index in range(count)
    ]
    path.write_text(json.dumps(records), encoding="utf-8")


def _manifest(path, ids):
    path.write_text(
        json.dumps({"records": [{"id": task_id} for task_id in ids]}),
        encoding="utf-8",
    )


def test_r3_cohort_is_deterministic_and_excludes_every_prior_frame(tmp_path):
    dataset = tmp_path / "dataset.json"
    scored = tmp_path / "scored.json"
    r1 = tmp_path / "r1.json"
    r2 = tmp_path / "r2.json"
    _write_dataset(dataset)
    _manifest(scored, [f"{index:03d}" for index in range(100)])
    _manifest(r1, [f"{index:03d}" for index in range(100, 104)])
    _manifest(r2, [f"{index:03d}" for index in range(104, 124)])

    first = generate(
        output_dir=tmp_path / "first",
        dataset_path=dataset,
        exclusion_manifests=[scored, r1, r2],
    )
    second = generate(
        output_dir=tmp_path / "second",
        dataset_path=dataset,
        exclusion_manifests=[scored, r1, r2],
    )

    assert first == second
    manifest = json.loads((tmp_path / "first" / "R3_MANIFEST.json").read_text())
    schedule = json.loads((tmp_path / "first" / "R3_SCHEDULE.json").read_text())
    ids = {record["id"] for record in manifest["records"]}
    assert len(ids) == 30
    assert ids.isdisjoint({f"{index:03d}" for index in range(124)})
    assert all(row["order_reversal"] for row in schedule)
    assert first["excluded_id_count"] == 124
