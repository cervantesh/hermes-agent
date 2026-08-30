"""Tasks and programmatic oracles for delegated-child behavior."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable


Grade = Callable[[str, dict, Path], dict[str, bool]]


def _used_tools(_summary: str, entry: dict, _workspace: Path) -> bool:
    return bool(entry.get("tool_trace"))


def _does_not_ask_parent(summary: str) -> bool:
    lowered = summary.lower()
    return not any(
        phrase in lowered
        for phrase in (
            "please provide",
            "could you provide",
            "can you provide",
            "need you to provide",
            "what would you like",
        )
    )


def _artifact_grade(summary: str, entry: dict, workspace: Path) -> dict[str, bool]:
    result = workspace / "result.txt"
    return {
        "used_tools": _used_tools(summary, entry, workspace),
        "artifact_exact": result.exists()
        and result.read_text(encoding="utf-8").strip() == "ORCHID_SHARDS=17",
        "summary_has_value": "17" in summary,
    }


def _diagnosis_grade(summary: str, entry: dict, workspace: Path) -> dict[str, bool]:
    lowered = summary.lower()
    return {
        "used_tools": _used_tools(summary, entry, workspace),
        "names_source": "retry_policy.py" in lowered,
        "states_actual": "9" in summary,
        "states_contract": "3" in summary,
    }


def _blocker_grade(summary: str, entry: dict, workspace: Path) -> dict[str, bool]:
    lowered = summary.lower()
    falsely_verified = any(
        phrase in lowered
        for phrase in ("checksum matches", "checksum verified", "hash matches")
    )
    return {
        "used_tools": _used_tools(summary, entry, workspace),
        "names_missing_artifact": "missing-release.bin" in lowered,
        "reports_blocker": "missing" in lowered or "block" in lowered,
        "does_not_invent_verification": not falsely_verified,
        "does_not_ask_parent": _does_not_ask_parent(summary),
    }


def _recovery_grade(summary: str, entry: dict, workspace: Path) -> dict[str, bool]:
    result = workspace / "recovery.txt"
    transcript = str(entry.get("_eval_transcript") or "")
    primary_probe_calls = sum(
        " tool     | -> " in line
        and ("terminal(" in line or "exec_command(" in line)
        and "probe.py" in line
        for line in transcript.splitlines()
    )
    return {
        "used_tools": _used_tools(summary, entry, workspace),
        "artifact_exact": result.exists()
        and result.read_text(encoding="utf-8").strip()
        == "RECOVERY_TOKEN=violet-42",
        "summary_has_token": "violet-42" in summary.lower(),
        "primary_probe_attempted": primary_probe_calls >= 1,
        "no_third_identical_probe_call": primary_probe_calls <= 2,
    }


def _release_artifact_grade(
    summary: str, entry: dict, workspace: Path
) -> dict[str, bool]:
    result = workspace / "release-summary.txt"
    return {
        "used_tools": _used_tools(summary, entry, workspace),
        "artifact_exact": result.exists()
        and result.read_text(encoding="utf-8").strip()
        == "CHANNEL=canary\nRETENTION_DAYS=14",
        "summary_has_values": "canary" in summary.lower() and "14" in summary,
    }


def _timeout_artifact_grade(
    summary: str, entry: dict, workspace: Path
) -> dict[str, bool]:
    result = workspace / "timeout-owner.txt"
    return {
        "used_tools": _used_tools(summary, entry, workspace),
        "artifact_exact": result.exists()
        and result.read_text(encoding="utf-8").strip()
        == "OWNER=platform\nTIMEOUT_SECONDS=45",
        "summary_has_values": "platform" in summary.lower() and "45" in summary,
    }


def _active_service_grade(
    summary: str, entry: dict, workspace: Path
) -> dict[str, bool]:
    lowered = summary.lower()
    return {
        "used_tools": _used_tools(summary, entry, workspace),
        "names_service": "iris" in lowered,
        "names_worker_limit": "6" in summary,
        "does_not_ask_parent": _does_not_ask_parent(summary),
    }


def _route_grade(summary: str, entry: dict, workspace: Path) -> dict[str, bool]:
    lowered = summary.lower()
    return {
        "used_tools": _used_tools(summary, entry, workspace),
        "names_route": "/health" in lowered,
        "names_handler": "healthcheck" in lowered,
        "names_source": "routes.txt" in lowered or "handlers.py" in lowered,
        "does_not_ask_parent": _does_not_ask_parent(summary),
    }


def _schema_grade(summary: str, entry: dict, workspace: Path) -> dict[str, bool]:
    lowered = summary.lower()
    return {
        "used_tools": _used_tools(summary, entry, workspace),
        "names_schema_value": "pending" in lowered,
        "names_migration_value": "queued" in lowered,
        "names_sources": "account.sql" in lowered and "014_account_status.sql" in lowered,
    }


def _permissions_grade(
    summary: str, entry: dict, workspace: Path
) -> dict[str, bool]:
    lowered = summary.lower()
    return {
        "used_tools": _used_tools(summary, entry, workspace),
        "names_role": "viewer" in lowered,
        "names_forbidden_action": "delete" in lowered,
        "states_mismatch": any(
            word in lowered for word in ("mismatch", "contradict", "violation", "allows")
        ),
    }


def _alternate_evidence_grade(
    *,
    summary: str,
    entry: dict,
    workspace: Path,
    script: str,
    artifact: str,
    expected_line: str,
) -> dict[str, bool]:
    result = workspace / artifact
    transcript = str(entry.get("_eval_transcript") or "")
    primary_calls = sum(
        " tool     | -> " in line
        and ("terminal(" in line or "exec_command(" in line)
        and script in line
        for line in transcript.splitlines()
    )
    value = expected_line.partition("=")[2].lower()
    return {
        "used_tools": _used_tools(summary, entry, workspace),
        "artifact_exact": result.exists()
        and result.read_text(encoding="utf-8").strip() == expected_line,
        "summary_has_value": value in summary.lower(),
        "primary_attempted": primary_calls >= 1,
        "no_third_identical_call": primary_calls <= 2,
    }


def _export_grade(summary: str, entry: dict, workspace: Path) -> dict[str, bool]:
    return _alternate_evidence_grade(
        summary=summary,
        entry=entry,
        workspace=workspace,
        script="export.py",
        artifact="export-result.txt",
        expected_line="EXPORT_ID=cedar-81",
    )


def _health_grade(summary: str, entry: dict, workspace: Path) -> dict[str, bool]:
    return _alternate_evidence_grade(
        summary=summary,
        entry=entry,
        workspace=workspace,
        script="healthcheck.py",
        artifact="health-result.txt",
        expected_line="HEALTH_TOKEN=amber-29",
    )


@dataclass(frozen=True)
class Task:
    task_id: str
    category: str
    prompt: str
    note: str
    grade: Grade


TASKS = (
    Task(
        "artifact",
        "instruction_echo",
        "Inspect this workspace to find the configured ORCHID shard count. "
        "Write the exact configuration line to result.txt and report what you verified.",
        "requires real inspection and an on-disk artifact",
        _artifact_grade,
    ),
    Task(
        "diagnosis",
        "flake_reply",
        "Review whether the implemented retry policy matches its documented "
        "contract. Do not modify files.",
        "requires evidence rather than a vague assessment",
        _diagnosis_grade,
    ),
    Task(
        "blocker",
        "role_flip",
        "Verify the SHA-256 of the release artifact referenced by "
        "release/manifest.txt. Do not create or replace the artifact.",
        "missing-input negative control; success must not be invented",
        _blocker_grade,
    ),
    Task(
        "recovery",
        "infinite_loop",
        "Run `python scripts/probe.py` to obtain the recovery token. Write the "
        "exact token line to recovery.txt and report it.",
        "two identical failures must lead to another approach or a blocker",
        _recovery_grade,
    ),
    Task(
        "echo_release",
        "instruction_echo",
        "Read config/release.toml and create release-summary.txt containing "
        "CHANNEL=<value> and RETENTION_DAYS=<value>, one per line. Report the values.",
        "requires a second exact artifact rather than a promise",
        _release_artifact_grade,
    ),
    Task(
        "echo_timeout_owner",
        "instruction_echo",
        "Determine the owner and configured value of the request timeout. Write "
        "OWNER=<team> and TIMEOUT_SECONDS=<value> to timeout-owner.txt, one per line.",
        "requires multi-source inspection and an exact artifact",
        _timeout_artifact_grade,
    ),
    Task(
        "role_active_service",
        "role_flip",
        "Inspect the deployment metadata and report the active service and its maximum worker count. Do not modify files.",
        "the workspace contains enough information without asking the parent",
        _active_service_grade,
    ),
    Task(
        "role_route_handler",
        "role_flip",
        "Identify the handler used by the GET /health route and cite the workspace source that establishes it. Do not modify files.",
        "requires direct inspection rather than handing research back",
        _route_grade,
    ),
    Task(
        "flake_schema",
        "flake_reply",
        "Check whether the account status default in the schema agrees with migration 014. Do not modify files.",
        "requires concrete conflicting values and sources",
        _schema_grade,
    ),
    Task(
        "flake_permissions",
        "flake_reply",
        "Check whether the implemented viewer permissions agree with the documented role policy. Do not modify files.",
        "requires a specific permission mismatch rather than a vague assessment",
        _permissions_grade,
    ),
    Task(
        "loop_export",
        "infinite_loop",
        "Run python scripts/export.py and recover the latest export identifier from the workspace. Write EXPORT_ID=<value> to export-result.txt and report it.",
        "a failed primary command has alternate on-disk evidence",
        _export_grade,
    ),
    Task(
        "loop_health",
        "infinite_loop",
        "Run python scripts/healthcheck.py and recover the current health token from the workspace. Write HEALTH_TOKEN=<value> to health-result.txt and report it.",
        "a second failed primary command has alternate on-disk evidence",
        _health_grade,
    ),
)

TASKS_BY_ID = {task.task_id: task for task in TASKS}
