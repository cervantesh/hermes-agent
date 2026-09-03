"""Create the prospective V7 protocol seal exactly once."""

from __future__ import annotations

from datetime import datetime, timezone
import json

from .protocol import CAMEL_REVISION, FREEZE_ID, HERMES_REVISION
from .source_manifest import ROOT, manifest


def main() -> int:
    path = ROOT / "PROTOCOL_SEAL.json"
    payload = {
        "freeze_id": FREEZE_ID,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "hermes_revision": HERMES_REVISION,
        "camel_revision": CAMEL_REVISION,
        "manifest": manifest(),
        "status": "PROSPECTIVE_NO_PROVIDER_OBSERVATIONS",
    }
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
