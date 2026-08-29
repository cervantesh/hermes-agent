"""Exercise Hermes' Windows service stop/start helpers against real SCM."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import psutil

from hermes_cli import update_cmd


SERVICE = "HermesCodexSupervisorE2E"
evidence_dir = Path(os.environ["EVIDENCE_DIR"])


def running_identity() -> tuple[int, float]:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        status = psutil.win_service_get(SERVICE).as_dict()
        pid = int(status.get("pid") or 0)
        if status.get("status") == "running" and pid > 0:
            process = psutil.Process(pid)
            return pid, process.create_time()
        time.sleep(0.25)
    raise AssertionError("SCM service did not reach running state")


old_pid, old_created = running_identity()
update_cmd._stop_windows_gateway_service(
    SERVICE,
    expected_service_identity=(old_pid, old_created),
    expected_processes=[(old_pid, old_created)],
    timeout=30.0,
)
stopped = psutil.win_service_get(SERVICE).status() == "stopped"
old_gone = not psutil.pid_exists(old_pid)
update_cmd._start_windows_gateway_service(SERVICE, timeout=30.0)
new_pid, _new_created = running_identity()

assert stopped
assert old_gone
assert new_pid != old_pid

outcome = {
    "frame": os.environ["FRAME"],
    "source_sha": os.environ["SOURCE_SHA"],
    "supervisor": "windows-scm",
    "contract": {
        "real_service_running_before": True,
        "hermes_stop_path_completed": True,
        "service_stopped_and_old_pid_gone": True,
        "hermes_start_path_completed": True,
        "pid_rotated": True,
        "service_running_after": True,
    },
}
(evidence_dir / "outcome.json").write_text(
    json.dumps(outcome, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
print(json.dumps(outcome, indent=2, sort_keys=True))
