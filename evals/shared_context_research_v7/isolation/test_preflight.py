from __future__ import annotations

from pathlib import Path

from hermes_cli import kanban_db as kb

from ..common.hermes_fixture import read_task_through_kanban_show
from .preflight import classify_current_read


def test_unrelated_same_board_task_is_reachable_but_not_labeled_vulnerability(
    tmp_path: Path,
    monkeypatch,
) -> None:
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    kb.init_db()
    canary = "same-board-unrelated-canary-8f7be2"
    with kb.connect_closing() as conn:
        requester = kb.create_task(conn, title="requester")
        unrelated = kb.create_task(conn, title="unrelated", body=canary)

    visible = canary in read_task_through_kanban_show(unrelated).raw
    result = classify_current_read(
        requester_task=requester,
        owner_task=unrelated,
        relationship="unrelated_same_board",
        visible=visible,
    )

    assert result.visible
    assert result.candidate_policy_allows is False
    assert result.security_label == "POLICY_UNADJUDICATED"
    assert result.is_vulnerability is False


def test_declared_completed_parent_is_positive_control(
    tmp_path: Path,
    monkeypatch,
) -> None:
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    kb.init_db()
    canary = "declared-parent-canary-04a11d"
    with kb.connect_closing() as conn:
        parent = kb.create_task(conn, title="parent", body=canary)
        child = kb.create_task(conn, title="child")
        kb.link_tasks(conn, parent, child)
        kb.complete_task(conn, parent, result=canary)

    visible = canary in read_task_through_kanban_show(parent).raw
    result = classify_current_read(
        requester_task=child,
        owner_task=parent,
        relationship="declared_completed_parent",
        visible=visible,
    )

    assert result.visible
    assert result.candidate_policy_allows
    assert result.security_label == "POSITIVE_CONTROL"
