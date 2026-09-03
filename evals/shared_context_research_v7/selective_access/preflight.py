"""Deterministic Track 2 boundary preflight."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Iterable

from ..common.harness import OpaqueCorpus, exact_subset_digest, project_declared
from ..common.hermes_fixture import (
    CorpusGraph,
    read_task_through_kanban_show,
    worker_startup_context,
)


@dataclass(frozen=True)
class SelectiveAccessPreflight:
    source_result_bytes: int
    startup_contains_requested_value: bool
    kanban_show_result_exact: bool
    declared_result_exact: bool
    current_hermes_red: bool
    disposition: str


def run_selective_access_preflight(
    graph: CorpusGraph,
    corpus: OpaqueCorpus,
    requested_keys: Iterable[str],
) -> SelectiveAccessPreflight:
    requested = tuple(requested_keys)
    expected = exact_subset_digest(corpus.records, requested)
    requested_values = tuple(corpus.records[key] for key in requested)
    startup = worker_startup_context(graph.child_task)
    show = read_task_through_kanban_show(graph.parent_task)
    source_text = show.document["task"]["result"]
    full_payload = json.loads(source_text)
    declared = project_declared(corpus, requested)
    show_exact = exact_subset_digest(full_payload, requested) == expected
    declared_exact = exact_subset_digest(declared.payload, requested) == expected

    return SelectiveAccessPreflight(
        source_result_bytes=len(source_text.encode("utf-8")),
        startup_contains_requested_value=all(
            value in startup for value in requested_values
        ),
        kanban_show_result_exact=show_exact,
        declared_result_exact=declared_exact,
        current_hermes_red=not show_exact,
        disposition=(
            "EXISTING HERMES MECHANISM SUFFICIENT" if show_exact else "INCONCLUSIVE"
        ),
    )
