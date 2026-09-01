"""Installation-wide admission boundary for an external Hermes application."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import Any, Sequence


_SCHEMA_VERSION = 1
_RECURSION_ENV = "_HERMES_EXTERNAL_APPLICATION_ACTIVE"
_MARKER_RELATIVE = Path("state") / "application-boundary.json"
_bootstrap_decided = False


class BoundaryRejected(RuntimeError):
    """The boundary is armed but its durable contract cannot be honored."""


def installation_root() -> Path:
    configured = os.environ.get("HERMES_HOME", "").strip()
    if configured:
        root = Path(configured).expanduser().resolve()
        if root.parent.name == "profiles" and root.name:
            return root.parent.parent
        return root
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA", "").strip()
        return (Path(local) / "hermes" if local else Path.home() / ".hermes").resolve()
    return (Path.home() / ".hermes").resolve()


def marker_path() -> Path:
    return installation_root() / _MARKER_RELATIVE


def _sync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        fd = os.open(path, flags)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def _strict_atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
        _sync_directory(path.parent)
    finally:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass


def _configuration_digest(command: Sequence[str]) -> str:
    encoded = json.dumps(
        {"application": {"external": {"command": list(command)}}},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _resolve_executable(value: str) -> Path:
    if not value or not value.strip():
        raise BoundaryRejected("external application command has an empty executable")
    candidate = Path(value).expanduser()
    resolved_value = os.fspath(candidate) if candidate.is_absolute() or candidate.parent != Path(".") else shutil.which(value)
    if not resolved_value:
        raise BoundaryRejected("external application executable cannot be resolved")
    resolved = Path(resolved_value).resolve(strict=True)
    info = resolved.stat()
    if not stat.S_ISREG(info.st_mode):
        raise BoundaryRejected("external application executable is not a regular file")
    if os.name == "nt" and resolved.suffix.lower() in {".cmd", ".bat"}:
        raise BoundaryRejected("Windows batch files are not valid external application executables")
    if os.name != "nt" and not os.access(resolved, os.X_OK):
        raise BoundaryRejected("external application executable is not executable")
    return resolved


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_command(root: Path | None = None) -> list[str]:
    import yaml

    config_path = (root or installation_root()) / "config.yaml"
    try:
        document = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        command = document["application"]["external"]["command"]
    except (OSError, TypeError, KeyError, yaml.YAMLError) as exc:
        raise BoundaryRejected("external application command is missing or invalid") from exc
    if not isinstance(command, list) or not command or any(
        not isinstance(item, str) or not item.strip() for item in command
    ):
        raise BoundaryRejected("external application command must be a non-empty list of strings")
    return command


def _build_marker(command: Sequence[str]) -> dict[str, Any]:
    executable = _resolve_executable(command[0])
    return {
        "schema_version": _SCHEMA_VERSION,
        "configuration_digest": _configuration_digest(command),
        "executable": {
            "path": os.fspath(executable),
            "sha256": _file_sha256(executable),
        },
    }


def _read_marker(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BoundaryRejected("application boundary marker is unreadable") from exc
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version", "configuration_digest", "executable"
    } or payload.get("schema_version") != _SCHEMA_VERSION:
        raise BoundaryRejected("application boundary marker has an unsupported schema")
    executable = payload.get("executable")
    if not isinstance(executable, dict) or set(executable) != {"path", "sha256"}:
        raise BoundaryRejected("application boundary marker has invalid executable identity")
    return payload


def _validate_armed_state(path: Path) -> tuple[list[str], dict[str, Any]]:
    payload = _read_marker(path)
    command = _load_command()
    expected = _build_marker(command)
    if payload != expected:
        raise BoundaryRejected("application boundary configuration or executable identity drifted")
    return command, payload


def detect_launcher(argv: Sequence[str] | None = None) -> str | None:
    values = list(sys.argv if argv is None else argv)
    if not values:
        return None
    raw = values[0].replace("\\", "/")
    name = Path(raw).name.lower()
    stem = Path(name).stem
    if stem in {"hermes", "hermes-agent", "hermes-acp"}:
        return stem
    normalized = raw.lower()
    matches = {
        "run_agent.py": "hermes-agent",
        "batch_runner.py": "batch-runner",
        "cli.py": "hermes",
        "acp_adapter/entry.py": "hermes-acp",
        "gateway/run.py": "gateway",
        "tui_gateway/entry.py": "tui-gateway",
        "cron/scheduler.py": "cron-scheduler",
        "hermes_cli/main.py": "hermes",
    }
    for suffix, launcher in matches.items():
        if normalized.endswith(suffix):
            return launcher
    return None


def admit(argv: Sequence[str] | None = None, *, launcher: str | None = None) -> list[str] | None:
    values = list(sys.argv if argv is None else argv)
    selected = launcher or detect_launcher(values)
    if selected is None:
        return None
    path = marker_path()
    if not path.exists():
        return None
    if os.environ.get(_RECURSION_ENV):
        raise BoundaryRejected("recursive external application delegation is forbidden")
    command, _ = _validate_armed_state(path)
    return [*command, *values[1:]]


def manage(argv: Sequence[str]) -> int:
    values = list(argv)
    if len(values) != 2 or values[0] != "application" or values[1] not in {"status", "enable", "disable"}:
        print("usage: hermes application {status|enable|disable}", file=sys.stderr)
        return 2
    action = values[1]
    path = marker_path()
    if action == "enable":
        try:
            command = _load_command()
            _strict_atomic_json_write(path, _build_marker(command))
        except (BoundaryRejected, OSError) as exc:
            print(f"application boundary not enabled: {exc}", file=sys.stderr)
            return 1
        print("application boundary enabled")
        return 0
    if action == "disable":
        try:
            path.unlink()
            _sync_directory(path.parent)
        except FileNotFoundError:
            pass
        except OSError as exc:
            print(f"application boundary not disabled: {exc}", file=sys.stderr)
            return 1
        print("application boundary disabled")
        return 0
    if not path.exists():
        print("application boundary disabled")
        return 0
    try:
        _validate_armed_state(path)
    except BoundaryRejected as exc:
        print(f"application boundary invalid: {exc}", file=sys.stderr)
        return 1
    print("application boundary enabled and valid")
    return 0


def _print_version() -> int:
    try:
        version = importlib.metadata.version("hermes-agent")
    except importlib.metadata.PackageNotFoundError:
        version = "unknown"
    print(f"Hermes Agent {version}")
    return 0


def _delegate(command: Sequence[str]) -> int:
    environment = os.environ.copy()
    environment[_RECURSION_ENV] = "1"
    if os.name == "nt":
        process = subprocess.Popen(list(command), env=environment, shell=False)
        return process.wait()
    os.execvpe(command[0], list(command), environment)
    raise AssertionError("execvpe returned unexpectedly")


def bootstrap_admit(argv: Sequence[str] | None = None) -> None:
    global _bootstrap_decided
    values = list(sys.argv if argv is None else argv)
    launcher = detect_launcher(values)
    if launcher is None:
        return
    if _bootstrap_decided:
        return
    _bootstrap_decided = True
    arguments = values[1:]
    if launcher == "hermes" and arguments[:1] == ["application"]:
        raise SystemExit(manage(arguments))
    path = marker_path()
    if path.exists() and launcher == "hermes" and arguments == ["--version"]:
        raise SystemExit(_print_version())
    try:
        command = admit(values, launcher=launcher)
    except BoundaryRejected as exc:
        print(f"Hermes application boundary rejected launch: {exc}", file=sys.stderr)
        raise SystemExit(78) from exc
    if command is not None:
        raise SystemExit(_delegate(command))
