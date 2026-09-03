"""Build and resolve a content-addressed AI Society sample manifest."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


_FROZEN_FIELDS = ("original_task", "specified_task", "role_1", "role_2")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _role_name(value: str, expected_suffix: str) -> str:
    suffix = f"_RoleType.{expected_suffix}"
    if not value.endswith(suffix):
        raise ValueError(f"role {value!r} does not end with {suffix!r}")
    return value[: -len(suffix)]


def _load_conversations(source_path: Path) -> dict[str, dict[str, str]]:
    rows: list[dict[str, Any]] = json.loads(source_path.read_text(encoding="utf-8"))
    conversations: dict[str, dict[str, str]] = {}
    for row in rows:
        record_id = str(row["id"])
        fields = {field: str(row[field]) for field in _FROZEN_FIELDS}
        existing = conversations.setdefault(record_id, fields)
        for field in _FROZEN_FIELDS:
            if existing[field] != fields[field]:
                raise ValueError(
                    f"inconsistent {field} within conversation {record_id}"
                )
    return conversations


def build_sample_manifest(
    source_path: str | Path,
    *,
    sample_size: int,
    seed: str,
    exclude_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Select distinct conversation IDs without copying task text into the manifest."""
    path = Path(source_path)
    conversations = _load_conversations(path)
    excluded = set(exclude_ids or ())
    eligible = {
        record_id: fields
        for record_id, fields in conversations.items()
        if record_id not in excluded
    }
    if sample_size < 1 or sample_size > len(eligible):
        raise ValueError("sample_size must fit the number of distinct conversations")

    ranked = sorted(
        eligible,
        key=lambda record_id: (_sha256_text(f"{seed}|{record_id}"), record_id),
    )[:sample_size]
    records = []
    for record_id in ranked:
        fields = eligible[record_id]
        records.append({
            "id": record_id,
            "rank_sha256": _sha256_text(f"{seed}|{record_id}"),
            "original_task_sha256": _sha256_text(fields["original_task"]),
            "specified_task_sha256": _sha256_text(fields["specified_task"]),
            "assistant_role_sha256": _sha256_text(
                _role_name(fields["role_1"], "ASSISTANT")
            ),
            "user_role_sha256": _sha256_text(_role_name(fields["role_2"], "USER")),
        })
    manifest = {
        "schema_version": 1,
        "seed": seed,
        "source_sha256": _file_sha256(path),
        "sample_size": sample_size,
        "records": records,
    }
    if excluded:
        manifest["excluded_id_count"] = len(excluded)
        manifest["excluded_ids_sha256"] = _sha256_text("\n".join(sorted(excluded)))
    return manifest


def resolve_manifest(
    source_path: str | Path, manifest: dict[str, Any]
) -> list[dict[str, str]]:
    """Resolve task text from the pinned dataset and verify every content hash."""
    path = Path(source_path)
    if _file_sha256(path) != manifest["source_sha256"]:
        raise ValueError("dataset digest does not match manifest")
    conversations = _load_conversations(path)
    resolved = []
    for expected in manifest["records"]:
        record_id = expected["id"]
        if record_id not in conversations:
            raise ValueError(f"manifest record {record_id} is absent from dataset")
        fields = conversations[record_id]
        item = {
            "id": record_id,
            "original_task": fields["original_task"],
            "specified_task": fields["specified_task"],
            "assistant_role": _role_name(fields["role_1"], "ASSISTANT"),
            "user_role": _role_name(fields["role_2"], "USER"),
        }
        for name in ("original_task", "specified_task", "assistant_role", "user_role"):
            if _sha256_text(item[name]) != expected[f"{name}_sha256"]:
                raise ValueError(f"manifest hash mismatch for {record_id}.{name}")
        resolved.append(item)
    return resolved
