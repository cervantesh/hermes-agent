"""Deterministic workflow fixtures with executable external truth."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import heapq
import json
from pathlib import Path
import random
from typing import Any

from .shared_context import canonical_bytes


@dataclass(frozen=True)
class WorkflowTask:
    task_id: str
    topology: str
    dependent: bool
    source: Any | None
    consumer_local: Any
    expected: Any
    reads: tuple[str, ...] = ("handoff",)
    expansion_only: bool = False

    @property
    def handoff(self) -> Any | None:
        if self.source is None:
            return None
        if self.task_id == "multi_key_reconciliation":
            return self.source
        return {"handoff": self.source}


def _token(rng: random.Random, prefix: str) -> str:
    return f"{prefix}-{rng.getrandbits(48):012x}"


def _compact_release_map(rng: random.Random) -> WorkflowTask:
    names = [
        "agent",
        "gateway",
        "desktop",
        "tui",
        "scheduler",
        "memory",
        "plugins",
        "browser",
        "provider",
        "sessions",
        "kanban",
        "update",
    ]
    components = [
        {
            "name": name,
            "version": f"{1 + index // 4}.{index % 4}.{rng.randrange(1, 20)}",
            "checksum": _token(rng, "sha"),
        }
        for index, name in enumerate(names)
    ]
    release = ["gateway", "desktop", "sessions", "update"]
    source = {"components": components, "release": release}
    by_name = {item["name"]: item for item in components}
    expected = {"release": [by_name[name] for name in release]}
    return WorkflowTask(
        "compact_release_map", "detached_source", True, source, {}, expected
    )


def _ordered_dependency_plan(rng: random.Random) -> WorkflowTask:
    deps = {
        "collect": [],
        "normalize": ["collect"],
        "index": ["normalize"],
        "policy": ["normalize"],
        "route": ["index", "policy"],
        "render": ["route"],
        "audit": ["policy"],
        "publish": ["render", "audit"],
    }
    nodes = [
        {"id": node, "deps": parents, "digest": _token(rng, "node")}
        for node, parents in deps.items()
    ]
    remaining = {node: set(parents) for node, parents in deps.items()}
    ready = [node for node, parents in remaining.items() if not parents]
    heapq.heapify(ready)
    order: list[str] = []
    while ready:
        node = heapq.heappop(ready)
        order.append(node)
        for child in sorted(remaining):
            if node in remaining[child]:
                remaining[child].remove(node)
                if not remaining[child] and child not in order and child not in ready:
                    heapq.heappush(ready, child)
    digest = hashlib.sha256("\n".join(order).encode()).hexdigest()
    return WorkflowTask(
        "ordered_dependency_plan",
        "detached_source",
        True,
        {"nodes": nodes},
        {"tie_break": "lexicographic"},
        {"order": order, "sha256": digest},
    )


def _artifact_policy_join(rng: random.Random) -> WorkflowTask:
    tiers = ["gold", "silver", "bronze"]
    records = [
        {
            "id": f"r{index:02d}",
            "tier": tiers[index % 3],
            "score": 40 + rng.randrange(61),
            "opaque": _token(rng, "opaque"),
        }
        for index in range(18)
    ]
    policy = {"allowed_tiers": ["gold", "silver"], "minimum_score": 72}
    selected = [
        record
        for record in records
        if record["tier"] in policy["allowed_tiers"]
        and record["score"] >= policy["minimum_score"]
    ]
    return WorkflowTask(
        "artifact_policy_join",
        "shared_storage",
        True,
        {"records": records},
        policy,
        {"selected": selected},
    )


def _distractor_filtered_catalog(rng: random.Random) -> WorkflowTask:
    tenants = ["atlas", "boreal"]
    regions = ["na", "eu", "apac"]
    records = []
    for index in range(24):
        records.append({
            "id": f"c{index:02d}",
            "tenant": tenants[index % 2],
            "region": regions[index % 3],
            "epoch": 7 + index % 3,
            "value": _token(rng, "value"),
        })
    allow = ["c02", "c08", "c14", "c20"]
    query = {"tenant": "atlas", "region": "apac", "epoch": 9, "allow": allow}
    selected = [
        record
        for record in records
        if record["tenant"] == query["tenant"]
        and record["region"] == query["region"]
        and record["epoch"] == query["epoch"]
        and record["id"] in query["allow"]
    ]
    return WorkflowTask(
        "distractor_filtered_catalog",
        "detached_source",
        True,
        {"records": records},
        query,
        {"selected": selected},
    )


def _independent_control(task_id: str, topology: str) -> WorkflowTask:
    local = {
        "candidates": [
            {"id": "safe", "enabled": True, "priority": 3},
            {"id": "off", "enabled": False, "priority": 9},
            {"id": "low", "enabled": True, "priority": 1},
        ]
    }
    return WorkflowTask(
        task_id,
        topology,
        False,
        None,
        local,
        {"selected": "safe"},
        reads=(),
    )


def _multi_key(rng: random.Random) -> WorkflowTask:
    source = {
        "inventory": {"items": [_token(rng, "item") for _ in range(8)]},
        "policy": {"take": [1, 3, 6], "mode": "ordered"},
        "authority": {"revision": _token(rng, "rev"), "approved": True},
    }
    expected = {
        "revision": source["authority"]["revision"],
        "items": [source["inventory"]["items"][i] for i in source["policy"]["take"]],
    }
    return WorkflowTask(
        "multi_key_reconciliation",
        "detached_source",
        True,
        source,
        {},
        expected,
        reads=("inventory", "policy", "authority"),
        expansion_only=True,
    )


def _bounded_payload(rng: random.Random) -> WorkflowTask:
    records = [
        {"id": f"p{index:02d}", "blob": _token(rng, "payload") * 2}
        for index in range(52)
    ]
    source = {"records": records, "select": ["p03", "p21", "p49"]}
    by_id = {item["id"]: item for item in records}
    expected = {"selected": [by_id[item] for item in source["select"]]}
    return WorkflowTask(
        "bounded_payload_edge",
        "detached_source",
        True,
        source,
        {},
        expected,
        expansion_only=True,
    )


def build_tasks(seed: int = 377) -> tuple[WorkflowTask, ...]:
    rng = random.Random(seed)
    return (
        _compact_release_map(rng),
        _ordered_dependency_plan(rng),
        _artifact_policy_join(rng),
        _distractor_filtered_catalog(rng),
        _independent_control("independent_local_control", "shared_storage"),
        _independent_control("independent_detached_control", "detached_source"),
        _multi_key(rng),
        _bounded_payload(rng),
    )


def build_preflight_tasks() -> tuple[WorkflowTask, ...]:
    source = {"upstream_value": "alpha"}
    local = {"local_value": "beta"}
    expected = {"upstream_value": "alpha", "local_value": "beta"}
    return (
        WorkflowTask(
            "preflight_detached_echo",
            "detached_source",
            True,
            source,
            local,
            expected,
        ),
        WorkflowTask(
            "preflight_shared_echo",
            "shared_storage",
            True,
            source,
            local,
            expected,
        ),
    )


TASKS = build_tasks()
PREFLIGHT_TASKS = build_preflight_tasks()
TASKS_BY_ID = {task.task_id: task for task in TASKS + PREFLIGHT_TASKS}


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def consumer_operation(task: WorkflowTask) -> str:
    """Return the frozen operation without revealing the expected output."""
    if task.task_id.startswith("preflight_"):
        return (
            "Copy `upstream_value` from the handoff and `local_value` from "
            "consumer_input.json into result.json under those exact two keys."
        )
    if task.task_id == "compact_release_map":
        return (
            "Use the release name order from the handoff and emit those complete "
            "component records under the key `release`. Preserve every field."
        )
    if task.task_id == "ordered_dependency_plan":
        return (
            "Topologically order every node from the handoff. When multiple nodes "
            "are ready, choose lexicographically. Emit `order` and SHA-256 of the "
            "node ids joined by a newline under `sha256`."
        )
    if task.task_id == "artifact_policy_join":
        return (
            "Read the normalized handoff records and consumer_input.json. Emit "
            "under `selected` every complete record whose tier is allowed and "
            "whose score is at least minimum_score, preserving source order."
        )
    if task.task_id == "distractor_filtered_catalog":
        return (
            "Use consumer_input.json as the query. Emit under `selected` only "
            "complete handoff records matching tenant, region, epoch, and the "
            "allow list, preserving source order."
        )
    if task.task_id.startswith("independent_"):
        return (
            "Use only consumer_input.json. Emit `selected` with the id of the "
            "enabled candidate having the greatest priority."
        )
    if task.task_id == "multi_key_reconciliation":
        return (
            "Use the inventory, policy, and authority handoff values. Emit the "
            "authority revision and the inventory items at the ordered policy "
            "indexes under keys `revision` and `items`."
        )
    if task.task_id == "bounded_payload_edge":
        return (
            "Use the handoff select list and emit the corresponding complete "
            "records under `selected`, preserving select-list order."
        )
    raise KeyError(task.task_id)
