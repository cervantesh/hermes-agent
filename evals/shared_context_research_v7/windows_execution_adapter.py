"""Windows-only execution adapter for the prospectively sealed V7 runner.

This module changes no prompt, fixture, cohort, threshold, oracle, or stopping
rule.  It closes Hermes's process-wide asynchronous log handlers before the
sealed per-observation TemporaryDirectory is removed on Windows.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
from pathlib import Path
from typing import Iterator

import hermes_logging

from .common.preflight_runner import _isolated_hermes_home as _base_isolation
from .scored_runner import run_study


@contextmanager
def logging_safe_isolation() -> Iterator[str]:
    """Close global log handles before the sealed temporary home is removed."""

    with _base_isolation() as isolation_id:
        try:
            yield isolation_id
        finally:
            hermes_logging._reset_queued_handlers()
            hermes_logging._logging_initialized = False


def install() -> None:
    """Install the cleanup-only adapter at the two scored isolation sites."""

    from .context_cost import runner as context_runner
    from .isolation import runner as isolation_runner

    context_runner._isolated_hermes_home = logging_safe_isolation
    isolation_runner._isolated_hermes_home = logging_safe_isolation


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", required=True)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    install()
    receipt = run_study(
        evidence_root=Path(args.evidence_root).resolve(),
        label=args.label,
    )
    print(json.dumps({"observation_count": receipt["observation_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
