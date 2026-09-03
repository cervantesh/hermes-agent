"""Deterministic Track 1 preflight over the real Hermes read envelope."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Iterable

from ..common.harness import (
    OpaqueCorpus,
    exact_subset_digest,
    project_declared,
    project_full,
)
from ..common.hermes_fixture import (
    CorpusGraph,
    read_task_through_kanban_show,
    worker_startup_context,
)


@dataclass(frozen=True)
class ContextCostPreflight:
    full_result_exact: bool
    declared_result_exact: bool
    full_payload_bytes: int
    declared_payload_bytes: int
    kanban_show_bytes: int
    worker_context_bytes: int


def run_context_cost_preflight(
    graph: CorpusGraph,
    corpus: OpaqueCorpus,
    requested_keys: Iterable[str],
) -> ContextCostPreflight:
    requested = tuple(requested_keys)
    expected = exact_subset_digest(corpus.records, requested)
    show = read_task_through_kanban_show(graph.parent_task)
    full_text = show.document["task"]["result"]
    full_payload = json.loads(full_text)
    declared = project_declared(corpus, requested)
    startup = worker_startup_context(graph.child_task)

    return ContextCostPreflight(
        full_result_exact=exact_subset_digest(full_payload, requested) == expected,
        declared_result_exact=(
            exact_subset_digest(declared.payload, requested) == expected
        ),
        full_payload_bytes=project_full(corpus).utf8_bytes,
        declared_payload_bytes=declared.utf8_bytes,
        kanban_show_bytes=len(show.raw.encode("utf-8")),
        worker_context_bytes=len(startup.encode("utf-8")),
    )
