"""Deterministic probe of current main's parent-link projection."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

from .runtime import HANDOFF_CLOSE, HANDOFF_OPEN, PROTOCOL_TARGET
from .shared_context import canonical_bytes, digest_bytes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    args = parser.parse_args()
    repo = Path(args.repo_root).resolve()
    if repo.as_posix() not in sys.path:
        sys.path.insert(0, str(repo))
    import subprocess

    head = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()
    if head != PROTOCOL_TARGET:
        raise SystemExit(f"unexpected target: {head}")
    with tempfile.TemporaryDirectory(prefix="shared-context-kanban-probe-") as raw:
        root = Path(raw)
        old = dict(os.environ)
        os.environ.update({
            "HERMES_HOME": str(root / "home"),
            "HERMES_KANBAN_DB": str(root / "kanban.db"),
            "HERMES_KANBAN_WORKSPACES_ROOT": str(root / "workspaces"),
            "HERMES_KANBAN_BOARD": "projection-probe",
        })
        try:
            from hermes_cli import kanban_db as kb

            conn = kb.connect(board="projection-probe")
            value = {"opaque": ["a-17", "b-29"], "revision": "r-377"}
            payload = canonical_bytes(value)
            block = HANDOFF_OPEN + payload.decode() + HANDOFF_CLOSE
            parent = kb.create_task(
                conn,
                title="parent",
                assignee="producer",
                workspace_kind="dir",
                workspace_path=str(root / "parent"),
                board="projection-probe",
            )
            kb.complete_task(
                conn,
                parent,
                summary=block,
                metadata={"sha256": digest_bytes(payload), "byte_count": len(payload)},
            )
            child = kb.create_task(
                conn,
                title="child",
                assignee="consumer",
                workspace_kind="dir",
                workspace_path=str(root / "child"),
                parents=(parent,),
                board="projection-probe",
            )
            context = kb.build_worker_context(conn, child)
            result = {
                "target": head,
                "parent_results": "## Parent task results" in context,
                "block_exact": block in context,
                "metadata_digest": digest_bytes(payload) in context,
                "child_status": kb.get_task(conn, child).status,
            }
            conn.close()
        finally:
            os.environ.clear()
            os.environ.update(old)
    print(json.dumps(result, sort_keys=True))
    return 0 if all(value for key, value in result.items() if key != "target") else 1


if __name__ == "__main__":
    raise SystemExit(main())
