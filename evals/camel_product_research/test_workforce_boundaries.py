"""Real-process characterization of Hermes's durable delegation boundary."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap


def _run(code: str, *, repo: Path, home: Path) -> dict:
    env = dict(os.environ)
    env["HERMES_HOME"] = str(home)
    env["PYTHONPATH"] = str(repo)
    env["PYTHONUTF8"] = "1"
    run = subprocess.run(
        [sys.executable, "-c", code],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    assert run.returncode == 0, run.stderr
    return json.loads(run.stdout.splitlines()[-1])


def test_owner_death_recovers_unknown_not_resumed_execution(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    home = tmp_path / ".hermes"
    home.mkdir()
    dispatch = textwrap.dedent(
        """
        import json
        import os
        import time
        from tools.async_delegation import dispatch_async_delegation

        def runner():
            time.sleep(60)
            return {"status": "completed", "summary": "late"}

        result = dispatch_async_delegation(
            goal="real owner-death boundary witness",
            context=None,
            toolsets=None,
            role="leaf",
            model="fixture",
            session_key="session-owner-death",
            runner=runner,
        )
        print(json.dumps(result), flush=True)
        os._exit(0)
        """
    )
    dispatched = _run(dispatch, repo=repo, home=home)
    delegation_id = dispatched["delegation_id"]

    recover = textwrap.dedent(
        f"""
        import json
        from tools.async_delegation import (
            get_durable_delegation,
            recover_abandoned_delegations,
        )
        count = recover_abandoned_delegations()
        record = get_durable_delegation({delegation_id!r})
        print(json.dumps({{"count": count, "record": record}}))
        """
    )
    recovered = _run(recover, repo=repo, home=home)
    assert recovered["count"] == 1
    assert recovered["record"]["state"] == "unknown"
    result = recovered["record"]["result"]
    assert result["status"] == "unknown"
    assert "outcome unknown" in result["error"].lower()
