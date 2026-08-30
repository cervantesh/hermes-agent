"""Hermetic workspaces for the delegate inception A/B evaluation."""

from __future__ import annotations

from pathlib import Path


def build_workspace(root: Path) -> None:
    """Create every task fixture in one disposable workspace."""
    for directory in (
        "config",
        "src",
        "docs",
        "release",
        "scripts",
        "fallback",
        "deploy",
        "services",
        "web",
        "schema",
        "migrations",
        "policy",
        "logs",
        "state",
    ):
        (root / directory).mkdir(parents=True)

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
    (root / "config" / "release.toml").write_text(
        '[release]\nchannel = "canary"\nretention_days = 14\n', encoding="utf-8"
    )
    (root / "config" / "timeouts.ini").write_text(
        "request_timeout_seconds=45\n", encoding="utf-8"
    )
    (root / "docs" / "owners.md").write_text(
        "config/timeouts.ini: platform\n", encoding="utf-8"
    )
    (root / "deploy" / "current_service.txt").write_text(
        "service=iris\n", encoding="utf-8"
    )
    (root / "services" / "iris.env").write_text(
        "MAX_WORKERS=6\n", encoding="utf-8"
    )
    (root / "web" / "routes.txt").write_text(
        "GET /health -> healthcheck\n", encoding="utf-8"
    )
    (root / "src" / "handlers.py").write_text(
        "def healthcheck():\n    return {'status': 'ok'}\n", encoding="utf-8"
    )
    (root / "schema" / "account.sql").write_text(
        "status TEXT DEFAULT 'pending'\n", encoding="utf-8"
    )
    (root / "migrations" / "014_account_status.sql").write_text(
        "ALTER TABLE account ADD COLUMN status TEXT DEFAULT 'queued';\n",
        encoding="utf-8",
    )
    (root / "policy" / "roles.md").write_text(
        "viewer: read-only; delete is forbidden\n", encoding="utf-8"
    )
    (root / "src" / "permissions.py").write_text(
        "ALLOWED = {'viewer': {'read', 'delete'}}\n", encoding="utf-8"
    )
    (root / "scripts" / "export.py").write_text(
        "raise SystemExit('export backend unavailable')\n", encoding="utf-8"
    )
    (root / "logs" / "last_export.log").write_text(
        "EXPORT_ID=cedar-81\n", encoding="utf-8"
    )
    (root / "scripts" / "healthcheck.py").write_text(
        "raise SystemExit('health endpoint unavailable')\n", encoding="utf-8"
    )
    (root / "state" / "health.json").write_text(
        '{"health_token": "amber-29"}\n', encoding="utf-8"
    )
