from __future__ import annotations

import sqlite3

from .runtime_v6 import _has_session, session_details_v6
from .runner_v6 import _digest


def test_session_probe_skips_sqlite_without_sessions_table(tmp_path) -> None:
    path = tmp_path / "state.db"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE unrelated (id TEXT)")
    conn.close()
    assert not _has_session(path, "worker-session")


def test_session_probe_matches_exact_session(tmp_path) -> None:
    path = tmp_path / "state.db"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE sessions (id TEXT PRIMARY KEY)")
    conn.execute("INSERT INTO sessions VALUES ('wanted')")
    conn.commit()
    conn.close()
    assert _has_session(path, "wanted")
    assert not _has_session(path, "other")


def test_session_lookup_ignores_invalid_root_candidate(tmp_path) -> None:
    invalid = tmp_path / "state.db"
    conn = sqlite3.connect(invalid)
    conn.execute("CREATE TABLE unrelated (id TEXT)")
    conn.close()

    valid = tmp_path / "profiles" / "producer" / "state.db"
    valid.parent.mkdir(parents=True)
    conn = sqlite3.connect(valid)
    conn.execute(
        "CREATE TABLE sessions ("
        "id TEXT PRIMARY KEY, api_call_count INTEGER, input_tokens INTEGER, "
        "output_tokens INTEGER, cache_read_tokens INTEGER, "
        "cache_write_tokens INTEGER, reasoning_tokens INTEGER, "
        "estimated_cost_usd REAL)"
    )
    conn.execute(
        "CREATE TABLE messages (id INTEGER PRIMARY KEY, session_id TEXT, "
        "role TEXT, tool_name TEXT, tool_calls TEXT, finish_reason TEXT)"
    )
    conn.execute("INSERT INTO sessions VALUES ('wanted', 1, 2, 3, 4, 5, 6, 0.0)")
    conn.commit()
    conn.close()

    details = session_details_v6(tmp_path, "wanted")

    assert details["session_found"] is True
    assert details["tokens"]["total_tokens"] == 20


def test_failure_digest_is_stable() -> None:
    assert _digest("failure") == _digest("failure")
    assert _digest("failure") != _digest("other")
