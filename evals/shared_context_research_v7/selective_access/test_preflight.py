from __future__ import annotations

from pathlib import Path

from hermes_cli import kanban_db as kb

from ..common.harness import OpaqueCorpus
from ..common.hermes_fixture import install_corpus_graph
from .preflight import run_selective_access_preflight


def test_above_cap_startup_loss_is_recoverable_through_real_kanban_show(
    tmp_path: Path,
    monkeypatch,
) -> None:
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    kb.init_db()
    corpus = OpaqueCorpus.generate(seed=81, record_count=100, value_bytes=128)
    requested = (corpus.keys[-1],)
    graph = install_corpus_graph(corpus)

    result = run_selective_access_preflight(graph, corpus, requested)

    assert result.source_result_bytes > kb._CTX_MAX_FIELD_BYTES
    assert not result.startup_contains_requested_value
    assert result.kanban_show_result_exact
    assert result.declared_result_exact
    assert result.current_hermes_red is False
    assert result.disposition == "EXISTING HERMES MECHANISM SUFFICIENT"


def test_below_cap_control_is_present_at_worker_startup(
    tmp_path: Path,
    monkeypatch,
) -> None:
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    kb.init_db()
    corpus = OpaqueCorpus.generate(seed=82, record_count=5, value_bytes=64)
    requested = (corpus.keys[-1],)
    graph = install_corpus_graph(corpus)

    result = run_selective_access_preflight(graph, corpus, requested)

    assert result.source_result_bytes < kb._CTX_MAX_FIELD_BYTES
    assert result.startup_contains_requested_value
    assert result.kanban_show_result_exact
