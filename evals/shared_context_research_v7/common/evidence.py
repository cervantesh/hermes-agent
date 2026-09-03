"""Sealing, failure retention, and public-evidence helpers."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Iterable, Mapping, Any


def digest_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_manifest(root: Path, relative_paths: Iterable[str]) -> dict[str, str]:
    return {Path(name).as_posix(): digest_file(root / name) for name in relative_paths}


def verify_seal(root: Path, seal_path: Path) -> None:
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    expected = seal.get("manifest")
    if not isinstance(expected, dict) or not expected:
        raise RuntimeError("seal has no manifest")
    actual = build_manifest(root, expected)
    if actual != expected:
        changed = sorted(
            name for name in expected if expected.get(name) != actual.get(name)
        )
        raise RuntimeError(f"seal mismatch: {', '.join(changed)}")


@dataclass(frozen=True)
class EvidenceLedger:
    directory: Path

    @classmethod
    def create(cls, root: Path, label: str) -> "EvidenceLedger":
        if not label or Path(label).name != label:
            raise ValueError("label must be one safe path component")
        directory = root / label
        directory.mkdir(parents=True, exist_ok=False)
        return cls(directory=directory)

    @property
    def rows_path(self) -> Path:
        return self.directory / "observations.jsonl"

    @property
    def abort_path(self) -> Path:
        return self.directory / "ABORTED.json"

    def append(self, row: Mapping[str, Any]) -> None:
        serialized = json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        with self.rows_path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(serialized)
            stream.flush()
            os.fsync(stream.fileno())

    def abort(self, reason: Mapping[str, Any]) -> None:
        with self.abort_path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(
                json.dumps(reason, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
            )
            stream.flush()
            os.fsync(stream.fileno())


_PUBLIC_FIELDS = (
    "track",
    "arm",
    "cohort",
    "seed",
    "external_oracle",
    "prompt_bytes",
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "latency_ms",
    "result_digest",
    "tool_counts",
    "termination_reason",
    "protocol_violations",
    "product_status",
)


def sanitize_observation(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Return only explicitly approved aggregate fields."""

    return {name: raw[name] for name in _PUBLIC_FIELDS if name in raw}
