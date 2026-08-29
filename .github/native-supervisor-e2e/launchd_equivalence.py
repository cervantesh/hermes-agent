"""Exercise Hermes' launchd update restart against a real LaunchAgent."""

from __future__ import annotations

import json
import os
import plistlib
import subprocess
import sys
import time
from pathlib import Path

from hermes_cli import update_cmd
from hermes_cli import gateway


LABEL = "ai.hermes.gateway"
DOMAIN = f"gui/{os.getuid()}"
evidence_dir = Path(os.environ["EVIDENCE_DIR"])
daemon = evidence_dir / "launchd_daemon.py"
daemon.write_text("import time\nwhile True:\n    time.sleep(1)\n", encoding="utf-8")
plist_path = gateway.get_launchd_plist_path()
plist_path.parent.mkdir(parents=True, exist_ok=True)
plist_path.write_bytes(
    plistlib.dumps(
        {
            "Label": LABEL,
            "ProgramArguments": [sys.executable, str(daemon)],
            "RunAtLoad": True,
            "KeepAlive": True,
            "StandardOutPath": str(evidence_dir / "launchd.stdout.log"),
            "StandardErrorPath": str(evidence_dir / "launchd.stderr.log"),
        }
    )
)


def pid() -> int | None:
    _loaded, value = gateway._launchd_print_service_pid(DOMAIN, LABEL)
    return value


target = f"{DOMAIN}/{LABEL}"
subprocess.run(["launchctl", "bootout", target], check=False, capture_output=True)
subprocess.run(
    ["launchctl", "bootstrap", DOMAIN, str(plist_path)],
    check=True,
    capture_output=True,
    text=True,
)
subprocess.run(["launchctl", "kickstart", target], check=True)
deadline = time.monotonic() + 15
old_pid = None
while time.monotonic() < deadline:
    old_pid = pid()
    if old_pid:
        break
    time.sleep(0.25)
assert old_pid and old_pid > 0

restarted, failed = update_cmd._restart_launchd_gateway_after_update(
    supervision_verify=True
)
new_pid = pid()
assert restarted == [LABEL], restarted
assert failed == [], failed
assert new_pid and new_pid > 0 and new_pid != old_pid

outcome = {
    "frame": os.environ["FRAME"],
    "source_sha": os.environ["SOURCE_SHA"],
    "supervisor": "launchd",
    "contract": {
        "real_agent_bootstrapped": True,
        "hermes_restart_path_completed": True,
        "pid_rotated": True,
        "agent_supervised_after_restart": True,
        "failed_labels_empty": True,
    },
}
(evidence_dir / "outcome.json").write_text(
    json.dumps(outcome, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
print(json.dumps(outcome, indent=2, sort_keys=True))
