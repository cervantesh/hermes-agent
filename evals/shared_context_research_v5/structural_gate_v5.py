"""Prove the selected tail value's reachability through current Kanban context."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from evals.shared_context_research.runtime import _json_block
from evals.shared_context_research.shared_context import canonical_bytes

from .protocol_v5 import TARGET_REVISION
from .tasks_v5 import build_tasks_v5


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    args = parser.parse_args()
    repo = Path(args.repo_root).resolve()
    head = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()
    dirty = bool(
        subprocess.check_output(
            ["git", "-C", str(repo), "status", "--porcelain"], text=True
        ).strip()
    )
    if head != TARGET_REVISION or dirty:
        raise SystemExit(f"target identity mismatch: head={head} dirty={dirty}")
    sys.path.insert(0, str(repo))
    rows = []
    with tempfile.TemporaryDirectory(prefix="shared-context-v5-structural-") as raw:
        old = dict(os.environ)
        root = Path(raw)
        os.environ.update({
            "HERMES_HOME": str(root / "home"),
            "HERMES_KANBAN_DB": str(root / "kanban.db"),
            "HERMES_KANBAN_WORKSPACES_ROOT": str(root / "workspaces"),
            "HERMES_KANBAN_BOARD": "v5-structural",
        })
        try:
            from hermes_cli import kanban_db as kb

            conn = kb.connect(board="v5-structural")
            for task in build_tasks_v5():
                payload = canonical_bytes(task.source).decode("utf-8")
                selected = task.expected["selected"][0]["opaque"]
                parent = kb.create_task(
                    conn,
                    title=f"parent {task.task_id}",
                    assignee="producer",
                    workspace_kind="dir",
                    workspace_path=str(root / f"parent-{task.task_id}"),
                    board="v5-structural",
                )
                kb.complete_task(conn, parent, summary=_json_block(task.source))
                child = kb.create_task(
                    conn,
                    title=f"child {task.task_id}",
                    assignee="consumer",
                    workspace_kind="dir",
                    workspace_path=str(root / f"child-{task.task_id}"),
                    parents=(parent,),
                    board="v5-structural",
                )
                context = kb.build_worker_context(conn, child)
                rows.append({
                    "task": task.task_id,
                    "source_payload_chars": len(payload),
                    "selected_tail_visible": selected in context,
                    "truncation_marker_visible": "chars omitted]" in context,
                })
            conn.close()
        finally:
            os.environ.clear()
            os.environ.update(old)
    receipt = {"target_revision": head, "target_dirty": dirty, "rows": rows}
    print(json.dumps(receipt, indent=2, sort_keys=True))
    below, above = rows
    valid = (
        below["source_payload_chars"] < 4096
        and below["selected_tail_visible"]
        and not below["truncation_marker_visible"]
        and above["source_payload_chars"] > 4096
        and not above["selected_tail_visible"]
        and above["truncation_marker_visible"]
    )
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
