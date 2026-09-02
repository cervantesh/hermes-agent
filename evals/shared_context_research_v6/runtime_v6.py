"""Compatibility repair for session evidence lookup on current main."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Any, Iterator

from evals.shared_context_research import runtime, runtime_v2
from evals.shared_context_research.runtime import RuntimeConfig
from evals.shared_context_research_v5.runtime_v5 import (
    run_b_gate_v5,
    run_comparison_v5,
)


_ORIGINAL_SESSION_DETAILS = runtime._session_details


def _has_session(path: Path, session_id: str) -> bool:
    if not path.is_file() or not session_id:
        return False
    conn = sqlite3.connect(path)
    try:
        table = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sessions'"
        ).fetchone()
        if not table:
            return False
        return (
            conn.execute(
                "SELECT 1 FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
            is not None
        )
    finally:
        conn.close()


def session_details_v6(home: Path, session_id: str) -> dict[str, Any]:
    """Select a session store by schema and identity, not filename alone."""

    candidates = [home / "state.db", *sorted((home / "profiles").glob("*/state.db"))]
    match = next((path for path in candidates if _has_session(path, session_id)), None)
    if match is None:
        return {"tools": [], "tokens": {}, "session_found": False}
    return _ORIGINAL_SESSION_DETAILS(match.parent, session_id)


@contextmanager
def _safe_session_lookup() -> Iterator[None]:
    original_runtime = runtime._session_details
    original_v2 = runtime_v2._session_details
    runtime._session_details = session_details_v6
    runtime_v2._session_details = session_details_v6
    try:
        yield
    finally:
        runtime._session_details = original_runtime
        runtime_v2._session_details = original_v2


def run_b_gate_v6(task, config: RuntimeConfig) -> dict[str, Any]:
    with _safe_session_lookup():
        return run_b_gate_v5(task, config)


def run_comparison_v6(
    task, schedule_seed: int, config: RuntimeConfig
) -> dict[str, Any]:
    with _safe_session_lookup():
        return run_comparison_v5(task, schedule_seed, config)
