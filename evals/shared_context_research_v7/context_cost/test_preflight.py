from __future__ import annotations

from pathlib import Path

from hermes_cli import kanban_db as kb

from ..common.harness import OpaqueCorpus
from ..common.hermes_fixture import install_corpus_graph
from .preflight import run_context_cost_preflight


def test_real_kanban_full_and_declared_projection_have_same_exact_result(
    tmp_path: Path,
    monkeypatch,
) -> None:
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    kb.init_db()
    corpus = OpaqueCorpus.generate(seed=71, record_count=80, value_bytes=96)
    requested = (corpus.keys[7], corpus.keys[73])
    graph = install_corpus_graph(corpus)

    result = run_context_cost_preflight(graph, corpus, requested)

    assert result.full_result_exact
    assert result.declared_result_exact
    assert result.declared_payload_bytes < result.full_payload_bytes
    assert result.kanban_show_bytes > result.full_payload_bytes
    assert result.worker_context_bytes > 0


def test_all_records_control_has_no_payload_size_advantage(
    tmp_path: Path,
    monkeypatch,
) -> None:
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    kb.init_db()
    corpus = OpaqueCorpus.generate(seed=72, record_count=12, value_bytes=32)
    graph = install_corpus_graph(corpus)

    result = run_context_cost_preflight(graph, corpus, corpus.keys)

    assert result.full_result_exact
    assert result.declared_result_exact
    assert result.declared_payload_bytes == result.full_payload_bytes
