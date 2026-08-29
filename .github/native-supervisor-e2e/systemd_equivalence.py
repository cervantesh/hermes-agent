"""Exercise Hermes' systemd unit iterator against a real ephemeral unit."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from hermes_cli import update_cmd


SERVICE = "hermes-serve-codex-e2e"


def _pid() -> int:
    result = subprocess.run(
        ["systemctl", "show", SERVICE, "--property=MainPID", "--value"],
        check=True,
        capture_output=True,
        text=True,
    )
    return int(result.stdout.strip())


listing = subprocess.run(
    [
        "systemctl",
        "list-units",
        "hermes-gateway*",
        "hermes-serve*",
        "--plain",
        "--no-legend",
        "--no-pager",
    ],
    check=True,
    capture_output=True,
    text=True,
).stdout
old_pid = _pid()
processed: list[str] = []
timeouts: list[str] = []


def restart(name: str) -> None:
    if name != SERVICE:
        return
    processed.append(name)
    subprocess.run(["sudo", "systemctl", "reset-failed", name], check=True)
    subprocess.run(["sudo", "systemctl", "restart", name], check=True)


update_cmd._for_each_systemd_gateway_unit(
    listing,
    process_unit=restart,
    on_unit_timeout=lambda name, _exc: timeouts.append(name),
)
new_pid = _pid()
active = subprocess.run(
    ["systemctl", "is-active", SERVICE], capture_output=True, text=True
).stdout.strip()

assert processed == [SERVICE], processed
assert not timeouts, timeouts
assert old_pid > 0 and new_pid > 0 and old_pid != new_pid
assert active == "active", active

outcome = {
    "frame": os.environ["FRAME"],
    "source_sha": os.environ["SOURCE_SHA"],
    "supervisor": "systemd",
    "contract": {
        "real_unit_discovered": True,
        "restart_completed": True,
        "pid_rotated": True,
        "unit_active_after_restart": True,
        "timeout_isolation_unused": True,
    },
}
path = Path(os.environ["EVIDENCE_DIR"]) / "outcome.json"
path.write_text(json.dumps(outcome, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(outcome, indent=2, sort_keys=True))
