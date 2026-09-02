"""Hash every source file that can affect V5 observations."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "shared_context_research/runtime.py",
    "shared_context_research/runtime_v2.py",
    "shared_context_research/shared_context.py",
    "shared_context_research/tasks.py",
    "shared_context_research_v3/durable_reader_v3.py",
    "shared_context_research_v3/runtime_v3.py",
    "shared_context_research_v5/tasks_v5.py",
    "shared_context_research_v5/runtime_v5.py",
    "shared_context_research_v5/structural_gate_v5.py",
    "shared_context_research_v5/protocol_v5.py",
    "shared_context_research_v5/fixture_worker_v5.py",
    "shared_context_research_v5/runner_v5.py",
    "shared_context_research_v5/RESEARCH_FRAME_V5.md",
    "shared_context_research_v5/PROTOCOL_FREEZE_V5.md",
)


def manifest() -> dict[str, str]:
    return {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in FILES
    }


def main() -> int:
    print(json.dumps(manifest(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
