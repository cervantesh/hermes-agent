"""Contract tests for the separate long-horizon evaluation suite."""

import re
import subprocess
import sys

from evals.delegate_inception.long_horizon import (
    LONG_TASKS,
    LONG_TASKS_BY_ID,
    build_long_workspace,
)
from evals.delegate_inception.worker import _load_suite


def test_long_suite_has_six_unique_ten_stage_workflows():
    assert len(LONG_TASKS) == 6
    assert len(LONG_TASKS_BY_ID) == 6
    assert len({task.task_id for task in LONG_TASKS}) == 6
    assert {task.category for task in LONG_TASKS} == {"long_horizon"}


def test_long_prompts_do_not_embed_candidate_directives():
    prompts = "\n".join(task.prompt.lower() for task in LONG_TASKS)

    assert "do not ask" not in prompts
    assert "do not restate" not in prompts
    assert "materially different approach" not in prompts
    assert "same failure twice" not in prompts


def test_worker_keeps_short_and_long_iteration_budgets_separate():
    short_task, short_builder, short_budget = _load_suite("short", "artifact")
    long_task, long_builder, long_budget = _load_suite("long", "long_release")

    assert short_task.task_id == "artifact"
    assert callable(short_builder)
    assert short_budget == 12
    assert long_task.task_id == "long_release"
    assert callable(long_builder)
    assert long_budget == 50


def test_fixture_can_complete_all_stages_via_declared_and_recovery_evidence(tmp_path):
    task = LONG_TASKS[0]
    build_long_workspace(tmp_path, task.task_id)
    driver = tmp_path / "scripts" / "next_stage.py"

    for _ in range(20):
        run = subprocess.run(
            [sys.executable, str(driver)],
            cwd=tmp_path,
            text=True,
            capture_output=True,
        )
        receipt = tmp_path / "final" / "receipt.txt"
        if receipt.exists():
            break
        match = re.search(
            r"Create (work/stage_\d+\.txt) with exact line: (STEP_\d+=\S+)",
            run.stdout,
        )
        if match:
            target = tmp_path / match.group(1)
            target.write_text(match.group(2) + "\n", encoding="utf-8")
            continue
        blocked = re.search(r"stage (\d+)", run.stderr)
        assert blocked, (run.stdout, run.stderr)
        stage = int(blocked.group(1))
        source = tmp_path / "recovery" / f"stage_{stage:02}.txt"
        target = tmp_path / "work" / f"stage_{stage:02}.txt"
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    assert receipt.read_text(encoding="utf-8").strip() == (
        f"WORKFLOW_COMPLETE={task.task_id}"
    )
    assert len(list((tmp_path / "work").glob("stage_*.txt"))) == 10
