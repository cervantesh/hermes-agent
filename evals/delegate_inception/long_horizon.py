"""Ten-stage workflows for observing late delegation failure modes."""

from __future__ import annotations

import json
from pathlib import Path
import textwrap

from tasks import Task, _does_not_ask_parent, _used_tools


_WORKFLOWS = (
    ("long_release", "release", 3),
    ("long_migration", "migration", 5),
    ("long_incident", "incident", 7),
    ("long_deployment", "deployment", 8),
    ("long_cache", "cache", 4),
    ("long_policy", "policy", 6),
)


def _expected_steps(task_id: str) -> dict[int, str]:
    stem = task_id.removeprefix("long_")
    return {
        stage: f"STEP_{stage:02}={stem}-{stage:02}-verified"
        for stage in range(1, 11)
    }


def _long_grade(task_id: str, blocked_stage: int):
    expected = _expected_steps(task_id)

    def grade(summary: str, entry: dict, workspace: Path) -> dict[str, bool]:
        receipt = workspace / "final" / "receipt.txt"
        audit = workspace / "audit" / "workflow.log"
        audit_text = audit.read_text(encoding="utf-8") if audit.exists() else ""
        blocked_count = audit_text.splitlines().count(f"stage={blocked_stage};status=blocked")
        stages_exact = all(
            (workspace / "work" / f"stage_{stage:02}.txt").is_file()
            and (workspace / "work" / f"stage_{stage:02}.txt")
            .read_text(encoding="utf-8")
            .strip()
            == line
            for stage, line in expected.items()
        )
        return {
            "used_tools": _used_tools(summary, entry, workspace),
            "receipt_exact": receipt.is_file()
            and receipt.read_text(encoding="utf-8").strip()
            == f"WORKFLOW_COMPLETE={task_id}",
            "all_ten_stages_exact": stages_exact,
            "all_ten_stages_verified": audit_text.count(";status=verified") == 10,
            "late_block_observed": blocked_count >= 1,
            "no_third_identical_block_retry": blocked_count <= 2,
            "summary_has_receipt": task_id in summary.lower(),
            "does_not_ask_parent": _does_not_ask_parent(summary),
            "completed_before_budget": entry.get("exit_reason") != "max_iterations",
        }

    return grade


LONG_TASKS = tuple(
    Task(
        task_id,
        "long_horizon",
        f"Complete the staged {theme} verification workflow in this workspace. "
        "Start by running `python scripts/next_stage.py`, follow the workflow "
        "until it writes final/receipt.txt, then report the receipt and the "
        "evidence recorded in audit/workflow.log.",
        f"ten dependent stages with an unavailable primary source at stage {blocked_stage}",
        _long_grade(task_id, blocked_stage),
    )
    for task_id, theme, blocked_stage in _WORKFLOWS
)

LONG_TASKS_BY_ID = {task.task_id: task for task in LONG_TASKS}


def build_long_workspace(root: Path, task_id: str) -> None:
    """Create one isolated stateful workflow with a late recoverable block."""
    if task_id not in LONG_TASKS_BY_ID:
        raise KeyError(task_id)
    blocked_stage = next(stage for name, _theme, stage in _WORKFLOWS if name == task_id)
    expected = _expected_steps(task_id)
    for directory in ("scripts", "work", "recovery", "final", "audit"):
        (root / directory).mkdir(parents=True, exist_ok=True)
    (root / "recovery" / f"stage_{blocked_stage:02}.txt").write_text(
        expected[blocked_stage] + "\n", encoding="utf-8"
    )
    config = {
        "task_id": task_id,
        "blocked_stage": blocked_stage,
        "steps": {str(stage): value for stage, value in expected.items()},
    }
    driver = textwrap.dedent(
        f"""
        import json
        from pathlib import Path
        import sys

        ROOT = Path(__file__).resolve().parents[1]
        CONFIG = {json.dumps(config, sort_keys=True)!r}
        CONFIG = json.loads(CONFIG)
        STATE = ROOT / ".workflow_state.json"
        AUDIT = ROOT / "audit" / "workflow.log"

        def log(stage, status):
            with AUDIT.open("a", encoding="utf-8") as sink:
                sink.write(f"stage={{stage}};status={{status}}\\n")

        state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {{"stage": 1}}
        stage = int(state["stage"])
        if stage > 10:
            print("workflow already complete")
            raise SystemExit(0)

        expected = CONFIG["steps"][str(stage)]
        target = ROOT / "work" / f"stage_{{stage:02}}.txt"
        if target.exists():
            if target.read_text(encoding="utf-8").strip() != expected:
                log(stage, "invalid")
                print(f"stage {{stage}} artifact is invalid", file=sys.stderr)
                raise SystemExit(1)
            log(stage, "verified")
            stage += 1
            STATE.write_text(json.dumps({{"stage": stage}}), encoding="utf-8")
            if stage > 10:
                receipt = ROOT / "final" / "receipt.txt"
                receipt.write_text("WORKFLOW_COMPLETE={task_id}\\n", encoding="utf-8")
                print(receipt.read_text(encoding="utf-8").strip())
                raise SystemExit(0)
            expected = CONFIG["steps"][str(stage)]
            target = ROOT / "work" / f"stage_{{stage:02}}.txt"

        if stage == int(CONFIG["blocked_stage"]):
            log(stage, "blocked")
            print(f"primary source unavailable for stage {{stage}}", file=sys.stderr)
            raise SystemExit(2)

        log(stage, "instructed")
        print(f"Create work/stage_{{stage:02}}.txt with exact line: {{expected}}")
        print("Then run this command again.")
        """
    ).lstrip()
    (root / "scripts" / "next_stage.py").write_text(driver, encoding="utf-8")
