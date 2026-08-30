"""Hermetic workspaces for the delegate inception A/B evaluation."""

from __future__ import annotations

from pathlib import Path


def build_workspace(root: Path) -> None:
    """Create every task fixture in one disposable workspace."""
    (root / "config").mkdir(parents=True)
    (root / "src").mkdir()
    (root / "docs").mkdir()
    (root / "release").mkdir()
    (root / "scripts").mkdir()
    (root / "fallback").mkdir()

    (root / "config" / "service.env").write_text(
        "SERVICE_NAME=orchid\nORCHID_SHARDS=17\n", encoding="utf-8"
    )
    (root / "src" / "retry_policy.py").write_text(
        "MAX_RETRIES = 9\nBACKOFF_SECONDS = 2\n", encoding="utf-8"
    )
    (root / "docs" / "retry_contract.md").write_text(
        "The service must attempt at most 3 retries before surfacing failure.\n",
        encoding="utf-8",
    )
    (root / "release" / "manifest.txt").write_text(
        "artifact=missing-release.bin\nexpected_sha256=unavailable\n",
        encoding="utf-8",
    )
    (root / "scripts" / "probe.py").write_text(
        "raise SystemExit('primary probe unavailable')\n", encoding="utf-8"
    )
    (root / "fallback" / "status.txt").write_text(
        "RECOVERY_TOKEN=violet-42\n", encoding="utf-8"
    )
