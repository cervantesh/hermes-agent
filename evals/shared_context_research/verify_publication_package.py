"""Build or verify the complete public issue #377 evidence package manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "PUBLICATION_MANIFEST.json"
EXCLUDED_PARTS = frozenset({"__pycache__", ".pytest_cache", "results-private"})


def public_files() -> dict[str, str]:
    files: dict[str, str] = {}
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path == MANIFEST:
            continue
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        key = relative.as_posix()
        files[key] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def build_manifest() -> dict[str, object]:
    files = public_files()
    return {
        "format": 1,
        "generated_on": "2026-09-02",
        "package": "hermes-agent-issue-377-shared-context-experiment",
        "target_revision": "180291162ff4df0d42b5dc4fecd08005cf7cebf9",
        "file_count": len(files),
        "files": files,
    }


def verify_manifest() -> dict[str, object]:
    expected = json.loads(MANIFEST.read_text(encoding="utf-8"))
    actual = build_manifest()
    if expected.get("format") != actual["format"]:
        raise ValueError("publication manifest format mismatch")
    if expected.get("package") != actual["package"]:
        raise ValueError("publication package identity mismatch")
    if expected.get("target_revision") != actual["target_revision"]:
        raise ValueError("publication target revision mismatch")
    if expected.get("file_count") != actual["file_count"]:
        raise ValueError("publication file count mismatch")
    if expected.get("files") != actual["files"]:
        missing = sorted(set(expected.get("files", {})) - set(actual["files"]))
        extra = sorted(set(actual["files"]) - set(expected.get("files", {})))
        changed = sorted(
            key
            for key in set(expected.get("files", {})) & set(actual["files"])
            if expected["files"][key] != actual["files"][key]
        )
        raise ValueError(
            f"publication files differ: missing={missing}, extra={extra}, "
            f"changed={changed}"
        )
    return {
        "ok": True,
        "file_count": actual["file_count"],
        "target_revision": actual["target_revision"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--write",
        action="store_true",
        help="regenerate PUBLICATION_MANIFEST.json from the current public tree",
    )
    args = parser.parse_args()
    if args.write:
        MANIFEST.write_text(
            json.dumps(build_manifest(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({"written": str(MANIFEST), **verify_manifest()}))
        return 0
    print(json.dumps(verify_manifest()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
