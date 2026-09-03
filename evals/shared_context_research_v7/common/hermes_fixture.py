"""Adapters that exercise the real Hermes Kanban read paths."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from hermes_cli import kanban_db as kb
from tools.kanban_tools import _handle_show

from .harness import OpaqueCorpus, project_full


@dataclass(frozen=True)
class CorpusGraph:
    parent_task: str
    child_task: str


@dataclass(frozen=True)
class KanbanShowResult:
    raw: str
    document: dict[str, Any]


def install_corpus_graph(corpus: OpaqueCorpus) -> CorpusGraph:
    """Create a completed producer and its declared consumer on a fresh board."""

    source = project_full(corpus).serialized.decode("utf-8")
    with kb.connect_closing() as conn:
        parent = kb.create_task(conn, title="opaque corpus producer")
        child = kb.create_task(conn, title="downstream selector")
        kb.link_tasks(conn, parent, child)
        kb.complete_task(conn, parent, result=source)
    return CorpusGraph(parent_task=parent, child_task=child)


def read_task_through_kanban_show(task_id: str) -> KanbanShowResult:
    """Call the registered handler path rather than reading SQLite directly."""

    raw = _handle_show({"task_id": task_id})
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"kanban_show returned non-JSON: {raw[:200]}") from exc
    if "task" not in document:
        raise RuntimeError(f"kanban_show failed: {document}")
    return KanbanShowResult(raw=raw, document=document)


def worker_startup_context(task_id: str) -> str:
    with kb.connect_closing() as conn:
        return kb.build_worker_context(conn, task_id)
