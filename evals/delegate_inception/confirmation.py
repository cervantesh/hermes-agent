"""Pre-registered long-horizon confirmation tasks for delegate inception."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import textwrap

from tasks import Task, _does_not_ask_parent, _used_tools


@dataclass(frozen=True)
class ConfirmationSpec:
    task_id: str
    archetype: str
    stages: tuple[str, ...]
    blocked_index: int
    recovery_dir: str


_SPECS = (
    ConfirmationSpec("confirm_release_train", "linear_checkpoint", ("inventory", "freeze", "build", "sign", "stage", "probe", "promote", "observe", "seal"), 6, "archive"),
    ConfirmationSpec("confirm_schema_rollout", "linear_checkpoint", ("snapshot", "plan", "shadow", "copy", "compare", "switch", "readback", "retire", "receipt", "close"), 7, "fallback"),
    ConfirmationSpec("confirm_key_rotation", "linear_checkpoint", ("enumerate", "issue", "distribute", "activate", "sample", "revoke", "audit", "persist", "confirm", "finish", "notify"), 8, "escrow"),
    ConfirmationSpec("confirm_index_rebuild", "linear_checkpoint", ("scope", "scan", "allocate", "populate", "validate", "swap", "query", "compact", "record"), 5, "snapshot"),
    ConfirmationSpec("confirm_failover_drill", "named_state_machine", ("armed", "isolated", "degraded", "redirected", "verified", "restored", "reconciled", "closed"), 5, "runbook"),
    ConfirmationSpec("confirm_certificate_renewal", "named_state_machine", ("discovered", "requested", "issued", "installed", "reloaded", "handshaken", "observed", "archived", "done"), 6, "vault"),
    ConfirmationSpec("confirm_queue_recovery", "named_state_machine", ("paused", "measured", "drained", "repaired", "replayed", "balanced", "resumed", "confirmed", "closed", "reported"), 7, "journal"),
    ConfirmationSpec("confirm_replica_reseed", "named_state_machine", ("selected", "fenced", "copied", "caught_up", "checked", "joined", "unfenced", "sampled", "accepted"), 5, "replica-log"),
    ConfirmationSpec("confirm_api_cutover", "two_lane_fanin", ("contract", "routing", "canary", "traffic", "stability", "completion"), 5, "mirror"),
    ConfirmationSpec("confirm_storage_move", "two_lane_fanin", ("catalog", "copy", "integrity", "permissions", "switch", "readback", "cleanup"), 6, "replica"),
    ConfirmationSpec("confirm_runtime_upgrade", "two_lane_fanin", ("resolve", "install", "compile", "smoke", "workload", "rollback", "accept"), 5, "cache"),
    ConfirmationSpec("confirm_policy_deploy", "two_lane_fanin", ("parse", "lint", "simulate", "approve", "publish", "enforce", "audit", "close"), 6, "evidence"),
    ConfirmationSpec("confirm_billing_reconcile", "event_ledger", ("open", "import", "normalize", "match", "dispute", "adjust", "balance", "readback", "post", "close"), 7, "ledger-copy"),
    ConfirmationSpec("confirm_session_restore", "event_ledger", ("locate", "claim", "load", "validate", "repair", "hydrate", "resume", "checkpoint", "readback"), 6, "recovery-log"),
    ConfirmationSpec("confirm_job_replay", "event_ledger", ("fence", "enumerate", "dedupe", "schedule", "execute", "collect", "reconcile", "release", "receipt", "finish"), 8, "dead-letter"),
    ConfirmationSpec("confirm_audit_backfill", "event_ledger", ("range", "extract", "order", "validate", "transform", "append", "compare", "seal", "publish", "verify", "close"), 9, "cold-log"),
    ConfirmationSpec("confirm_asset_bundle", "chunk_assembly", ("fonts", "icons", "styles", "runtime", "locales", "maps", "manifest", "signature"), 6, "vendor-cache"),
    ConfirmationSpec("confirm_model_package", "chunk_assembly", ("config", "tokenizer", "weights-a", "weights-b", "adapter", "license", "checksums", "index", "receipt"), 7, "registry-cache"),
    ConfirmationSpec("confirm_backup_restore", "chunk_assembly", ("catalog", "metadata", "segment-a", "segment-b", "segment-c", "wal", "permissions", "integrity", "receipt", "close"), 8, "offsite"),
    ConfirmationSpec("confirm_desktop_release", "chunk_assembly", ("python", "node", "renderer", "main", "resources", "installer", "symbols", "updates", "provenance", "receipt", "close"), 9, "build-cache"),
)


def _expected(spec: ConfirmationSpec) -> dict[int, str]:
    return {
        index: f"{name.upper().replace('-', '_')}={spec.task_id}-{index:02}-verified"
        for index, name in enumerate(spec.stages, start=1)
    }


def _grade(spec: ConfirmationSpec):
    expected = _expected(spec)

    def grade(summary: str, entry: dict, workspace: Path) -> dict[str, bool]:
        audit = workspace / "audit" / "events.jsonl"
        receipt = workspace / "final" / "receipt.txt"
        events = []
        if audit.exists():
            events = [json.loads(line) for line in audit.read_text(encoding="utf-8").splitlines() if line.strip()]
        blocked = [event for event in events if event == {"index": spec.blocked_index, "status": "blocked"}]
        required = []
        for index, line in expected.items():
            lanes = ("a", "b") if spec.archetype == "two_lane_fanin" else ("main",)
            for lane in lanes:
                suffix = f"-{lane}" if lane != "main" else ""
                required.append((workspace / "work" / f"{index:02}{suffix}.txt", line + (f";lane={lane}" if lane != "main" else "")))
        artifacts_exact = all(path.is_file() and path.read_text(encoding="utf-8").strip() == line for path, line in required)
        verified = [event for event in events if event.get("status") == "verified"]
        return {
            "used_tools": _used_tools(summary, entry, workspace),
            "all_required_artifacts_exact": artifacts_exact,
            "all_transitions_verified": len(verified) == len(spec.stages),
            "blocked_source_observed": bool(blocked),
            "no_third_identical_block_retry": len(blocked) <= 2,
            "receipt_exact": receipt.is_file() and receipt.read_text(encoding="utf-8").strip() == f"CONFIRMATION_COMPLETE={spec.task_id}",
            "summary_has_receipt": spec.task_id in summary.lower(),
            "does_not_ask_parent": _does_not_ask_parent(summary),
            "completed_before_budget": entry.get("exit_reason") != "max_iterations",
        }

    return grade


CONFIRMATION_TASKS = tuple(
    Task(
        spec.task_id,
        f"confirmation_{spec.archetype}",
        f"Complete the {spec.task_id.removeprefix('confirm_').replace('_', ' ')} workflow in this workspace. Start with `python scripts/advance.py`; continue until it emits the final receipt, then report that receipt and the verified event count from audit/events.jsonl.",
        f"{spec.archetype} with {len(spec.stages)} named stages and a late alternate-source recovery",
        _grade(spec),
    )
    for spec in _SPECS
)

CONFIRMATION_TASKS_BY_ID = {task.task_id: task for task in CONFIRMATION_TASKS}
_SPECS_BY_ID = {spec.task_id: spec for spec in _SPECS}


def build_confirmation_workspace(root: Path, task_id: str) -> None:
    spec = _SPECS_BY_ID[task_id]
    expected = _expected(spec)
    for directory in ("scripts", "work", spec.recovery_dir, "audit", "final"):
        (root / directory).mkdir(parents=True, exist_ok=True)
    blocked_line = expected[spec.blocked_index]
    if spec.archetype == "two_lane_fanin":
        blocked_line += ";lane=b"
    (root / spec.recovery_dir / "alternate.txt").write_text(blocked_line + "\n", encoding="utf-8")
    config = {
        "task_id": spec.task_id,
        "archetype": spec.archetype,
        "blocked_index": spec.blocked_index,
        "stages": list(spec.stages),
        "expected": {str(index): value for index, value in expected.items()},
    }
    driver = textwrap.dedent(
        f'''
        import json
        from pathlib import Path
        import sys

        ROOT = Path(__file__).resolve().parents[1]
        CONFIG = json.loads({json.dumps(json.dumps(config, sort_keys=True))})
        STATE = ROOT / ".confirmation_state.json"
        AUDIT = ROOT / "audit" / "events.jsonl"

        def log(index, status):
            with AUDIT.open("a", encoding="utf-8") as sink:
                sink.write(json.dumps({{"index": index, "status": status}}, sort_keys=True) + "\\n")

        state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {{"index": 1}}
        index = int(state["index"])
        total = len(CONFIG["stages"])
        if index > total:
            print("workflow already complete")
            raise SystemExit(0)

        expected = CONFIG["expected"][str(index)]
        lanes = ("a", "b") if CONFIG["archetype"] == "two_lane_fanin" else ("main",)
        paths = []
        for lane in lanes:
            suffix = f"-{{lane}}" if lane != "main" else ""
            paths.append((ROOT / "work" / f"{{index:02}}{{suffix}}.txt", expected + (f";lane={{lane}}" if lane != "main" else "")))

        if all(path.exists() and path.read_text(encoding="utf-8").strip() == value for path, value in paths):
            log(index, "verified")
            index += 1
            STATE.write_text(json.dumps({{"index": index}}), encoding="utf-8")
            if index > total:
                receipt = ROOT / "final" / "receipt.txt"
                receipt.write_text("CONFIRMATION_COMPLETE={spec.task_id}\\n", encoding="utf-8")
                print(receipt.read_text(encoding="utf-8").strip())
                raise SystemExit(0)
            expected = CONFIG["expected"][str(index)]
            lanes = ("a", "b") if CONFIG["archetype"] == "two_lane_fanin" else ("main",)
            paths = []
            for lane in lanes:
                suffix = f"-{{lane}}" if lane != "main" else ""
                paths.append((ROOT / "work" / f"{{index:02}}{{suffix}}.txt", expected + (f";lane={{lane}}" if lane != "main" else "")))

        if index == int(CONFIG["blocked_index"]):
            log(index, "blocked")
            print(f"preferred source unavailable for {{CONFIG['stages'][index - 1]}}", file=sys.stderr)
            raise SystemExit(2)

        log(index, "instructed")
        for path, value in paths:
            print(f"Create {{path.relative_to(ROOT)}} with exact line: {{value}}")
        print("Then run this command again.")
        '''
    ).lstrip()
    (root / "scripts" / "advance.py").write_text(driver, encoding="utf-8")
