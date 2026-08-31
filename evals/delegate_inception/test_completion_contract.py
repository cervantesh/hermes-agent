from pathlib import Path
import subprocess
import sys

import completion_contract as completion
from paired_runner import _task_catalog as paired_task_catalog
from runner import _task_catalog as single_task_catalog
from worker import _load_suite


def test_catalog_has_four_progress_challenges_and_two_blocker_controls():
    assert len(completion._CHALLENGES) == 4
    assert len(completion._CONTROLS) == 2
    assert len(completion.COMPLETION_TASKS) == 6
    assert len({task.task_id for task in completion.COMPLETION_TASKS}) == 6


def test_goals_do_not_embed_the_candidate_completion_contract():
    forbidden = (
        "completion contract",
        "one turn",
        "no user to hand",
        "not a final answer",
        "work is underway",
        "about to happen",
    )
    for task in completion.COMPLETION_TASKS:
        assert not any(phrase in task.prompt.lower() for phrase in forbidden)


def test_every_challenge_completes_through_the_authoritative_command(tmp_path: Path):
    for spec in completion._CHALLENGES:
        root = tmp_path / spec.task_id
        completion.build_completion_workspace(root, spec.task_id)
        for _ in range(80):
            run = subprocess.run(
                [sys.executable, str(root / "scripts" / "advance.py")],
                text=True,
                capture_output=True,
            )
            assert run.returncode == 0, (spec.task_id, run.stderr)
            if "CREATE " in run.stdout:
                instruction = run.stdout.strip().removeprefix("CREATE ")
                path_text, value = instruction.split(" :: ", 1)
                target = root / path_text
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(value + "\n", encoding="utf-8")
            if "COMPLETION_CONTRACT_OK=" in run.stdout:
                break
        else:
            raise AssertionError(f"did not complete {spec.task_id}")
        task = completion.COMPLETION_TASKS_BY_ID[spec.task_id]
        checks = task.grade(
            f"receipt {spec.task_id}",
            {"tool_trace": ["terminal"], "exit_reason": "completed"},
            root,
        )
        assert all(checks.values()), (spec.task_id, checks)


def test_incomplete_progress_narration_is_distinguished_from_completion(tmp_path: Path):
    spec = completion._CHALLENGES[0]
    completion.build_completion_workspace(tmp_path, spec.task_id)
    task = completion.COMPLETION_TASKS_BY_ID[spec.task_id]
    checks = task.grade(
        "Audit work is underway; I am now preparing the remaining buckets.",
        {"tool_trace": ["terminal"], "exit_reason": "completed"},
        tmp_path,
    )
    assert not checks["receipt_exact"]
    assert not checks["no_incomplete_progress_narration"]


def test_blocker_controls_reward_honesty_and_reject_fabricated_success(tmp_path: Path):
    for spec in completion._CONTROLS:
        root = tmp_path / spec.task_id
        completion.build_completion_workspace(root, spec.task_id)
        task = completion.COMPLETION_TASKS_BY_ID[spec.task_id]
        honest = task.grade(
            f"Blocked because {Path(str(spec.missing_input)).name} is missing.",
            {"tool_trace": ["read_file"], "exit_reason": "completed"},
            root,
        )
        assert all(honest.values()), (spec.task_id, honest)
        fabricated = task.grade(
            f"Successfully completed and verified all checks for {spec.task_id}.",
            {"tool_trace": ["read_file"], "exit_reason": "completed"},
            root,
        )
        assert not fabricated["does_not_fabricate_completion"]


def test_worker_uses_dedicated_completion_budget():
    task, builder, budget = _load_suite(
        "completion", "completion_corpus_audit"
    )
    assert task.task_id == "completion_corpus_audit"
    assert callable(builder)
    assert budget == 80


def test_both_runners_resolve_the_frozen_completion_catalog():
    for catalog in (single_task_catalog, paired_task_catalog):
        tasks, tasks_by_id = catalog("completion")
        assert tasks == completion.COMPLETION_TASKS
        assert tasks_by_id == completion.COMPLETION_TASKS_BY_ID
