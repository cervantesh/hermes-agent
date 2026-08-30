import json
from pathlib import Path
import subprocess
import sys

import confirmation


def test_confirmation_catalog_has_twenty_unique_tasks_across_five_archetypes():
    tasks = confirmation.CONFIRMATION_TASKS
    assert len(tasks) == 20
    assert len({task.task_id for task in tasks}) == 20
    assert len({task.category for task in tasks}) == 5


def test_every_confirmation_fixture_can_complete_via_alternate_source(tmp_path: Path):
    for task in confirmation.CONFIRMATION_TASKS:
        root = tmp_path / task.task_id
        confirmation.build_confirmation_workspace(root, task.task_id)
        spec = confirmation._SPECS_BY_ID[task.task_id]
        blocked_seen = False
        for _ in range(80):
            run = subprocess.run(
                [sys.executable, str(root / "scripts" / "advance.py")],
                text=True,
                capture_output=True,
            )
            if run.returncode == 2:
                assert not blocked_seen
                blocked_seen = True
                source = root / spec.recovery_dir / "alternate.txt"
                line = source.read_text(encoding="utf-8")
                suffix = "-b" if spec.archetype == "two_lane_fanin" else ""
                (root / "work" / f"{spec.blocked_index:02}{suffix}.txt").write_text(line, encoding="utf-8")
                if spec.archetype == "two_lane_fanin":
                    expected = confirmation._expected(spec)[spec.blocked_index]
                    (root / "work" / f"{spec.blocked_index:02}-a.txt").write_text(expected + ";lane=a\n", encoding="utf-8")
                continue
            assert run.returncode == 0, run.stderr
            for line in run.stdout.splitlines():
                if not line.startswith(("Create work/", "Create work\\")):
                    continue
                path_text, value = line.removeprefix("Create ").split(" with exact line: ", 1)
                (root / path_text).write_text(value + "\n", encoding="utf-8")
            if "CONFIRMATION_COMPLETE=" in run.stdout:
                break
        else:
            raise AssertionError(f"did not complete {task.task_id}")
        assert blocked_seen
        entry = {"tool_trace": ["terminal"]}
        checks = task.grade(task.task_id, entry, root)
        assert all(checks.values()), (task.task_id, checks)


def test_nominal_receipt_cannot_hide_a_skipped_required_stage(tmp_path: Path):
    task = confirmation.CONFIRMATION_TASKS_BY_ID["confirm_release_train"]
    confirmation.build_confirmation_workspace(tmp_path, task.task_id)
    (tmp_path / "final" / "receipt.txt").write_text(
        f"CONFIRMATION_COMPLETE={task.task_id}\n", encoding="utf-8"
    )
    (tmp_path / "audit" / "events.jsonl").write_text(
        "\n".join(json.dumps({"index": i, "status": "verified"}) for i in range(1, 10)) + "\n",
        encoding="utf-8",
    )
    checks = task.grade(task.task_id, {"tool_trace": ["terminal"]}, tmp_path)
    assert checks["receipt_exact"]
    assert not checks["all_required_artifacts_exact"]
