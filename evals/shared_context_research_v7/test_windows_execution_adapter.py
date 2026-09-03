from __future__ import annotations

from contextlib import contextmanager

import hermes_logging

from . import windows_execution_adapter as adapter


def test_cleanup_precedes_base_isolation_exit(monkeypatch) -> None:
    events: list[str] = []

    @contextmanager
    def fake_base():
        events.append("base-enter")
        try:
            yield "isolated"
        finally:
            events.append("base-exit")

    monkeypatch.setattr(adapter, "_base_isolation", fake_base)
    monkeypatch.setattr(
        hermes_logging,
        "_reset_queued_handlers",
        lambda: events.append("logging-reset"),
    )
    monkeypatch.setattr(hermes_logging, "_logging_initialized", True)

    with adapter.logging_safe_isolation() as isolation_id:
        assert isolation_id == "isolated"
        events.append("body")

    assert events == ["base-enter", "body", "logging-reset", "base-exit"]
    assert hermes_logging._logging_initialized is False


def test_install_replaces_only_scored_isolation_bindings() -> None:
    from .context_cost import runner as context_runner
    from .isolation import runner as isolation_runner

    adapter.install()

    assert context_runner._isolated_hermes_home is adapter.logging_safe_isolation
    assert isolation_runner._isolated_hermes_home is adapter.logging_safe_isolation
