"""Stdlib-only bootstrap authority for Hermes restricted mode.

This module is deliberately dependency-free.  Import-time guards use it before
dotenv, YAML, providers, plugins, tools, recovery, or UI code can run.
"""

from __future__ import annotations

import os
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

RESTRICTED_DIRNAME = "restricted-runtime"
AUTHORITY_FILENAME = "enabled"
RESERVED_CONFIG_NAME = b"restricted_runtime"
ENTRYPOINT_BLOCKED = "RESTRICTED_ENTRYPOINT_BLOCKED"
AUTHORITY_INVALID = "RESTRICTED_AUTHORITY_INVALID"

_PROCESS_AUTHORITY_ARMED = False


def _native_hermes_home() -> Path:
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA")
        return Path(local) / "hermes" if local else Path.home() / ".hermes"
    return Path.home() / ".hermes"


def resolve_global_hermes_root(
    hermes_home: str | os.PathLike[str] | None = None,
    *,
    native_home: Path | None = None,
) -> Path:
    """Resolve the installation-wide root without importing Hermes config."""

    native = Path(native_home) if native_home is not None else _native_hermes_home()
    raw = (
        os.environ.get("HERMES_HOME", "")
        if hermes_home is None
        else os.fspath(hermes_home)
    )
    if not raw:
        return native
    candidate = Path(raw)
    try:
        candidate.resolve(strict=False).relative_to(native.resolve(strict=False))
        return native
    except ValueError:
        if candidate.parent.name == "profiles":
            return candidate.parent.parent
        return candidate


def restricted_directory(root: Path | None = None) -> Path:
    return (root or resolve_global_hermes_root()) / RESTRICTED_DIRNAME


def authority_path(root: Path | None = None) -> Path:
    return restricted_directory(root) / AUTHORITY_FILENAME


def root_config_path(root: Path | None = None) -> Path:
    return (root or resolve_global_hermes_root()) / "config.yaml"


def _lexists(path: Path) -> bool:
    return os.path.lexists(os.fspath(path))


def authority_artifact_exists(root: Path | None = None) -> bool:
    return _lexists(authority_path(root))


def config_has_restricted_signal(path: Path | None = None) -> bool:
    """Conservatively detect the reserved name without interpreting YAML."""

    target = path or root_config_path()
    try:
        with open(target, "rb") as handle:
            overlap = b""
            while True:
                block = handle.read(64 * 1024)
                if not block:
                    return False
                combined = overlap + block
                if RESERVED_CONFIG_NAME in combined:
                    return True
                overlap = combined[-(len(RESERVED_CONFIG_NAME) - 1) :]
    except FileNotFoundError:
        return False
    except OSError:
        # An unreadable config cannot safely establish that restricted mode is
        # absent.  The safe resolver will later emit the closed authority error.
        return True


def _closed_invocation(argv: Sequence[str]) -> tuple[str, ...] | None:
    tokens = list(argv)
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in {"-p", "--profile"}:
            if index + 1 >= len(tokens):
                return None
            index += 2
            continue
        if token.startswith("--profile="):
            index += 1
            continue
        break
    if index < len(tokens) and tokens[index] == "restricted":
        return tuple(tokens[index + 1 :])
    return None


@dataclass(frozen=True)
class RestrictedBootstrapScanner:
    """Small argv/config scanner used before the full Hermes parser exists."""

    argv: Sequence[str]
    config_path: Path

    @property
    def restricted_invocation(self) -> tuple[str, ...] | None:
        return _closed_invocation(self.argv)

    @property
    def bare_candidate(self) -> bool:
        return len(self.argv) == 0

    @property
    def config_signal(self) -> bool:
        return config_has_restricted_signal(self.config_path)

    @property
    def authority_signal(self) -> bool:
        return authority_artifact_exists(self.config_path.parent)

    @property
    def route_is_closed(self) -> bool:
        return (
            self.restricted_invocation is not None
            or self.config_signal
            or self.authority_signal
        )


def arm_process_authority(root: Path | None = None) -> None:
    """Latch restricted authority for the remainder of this process."""

    global _PROCESS_AUTHORITY_ARMED
    if not authority_artifact_exists(root):
        raise RuntimeError(AUTHORITY_INVALID)
    _PROCESS_AUTHORITY_ARMED = True


def process_authority_is_armed() -> bool:
    return _PROCESS_AUTHORITY_ARMED


def should_block_normal_entrypoint(root: Path | None = None) -> bool:
    if _PROCESS_AUTHORITY_ARMED or authority_artifact_exists(root):
        return True
    return config_has_restricted_signal(root_config_path(root))


def emit_fixed_failure(symbol: str, exit_code: int) -> "None":
    try:
        sys.stderr.write(symbol + "\n")
        sys.stderr.flush()
    finally:
        raise SystemExit(exit_code)


def guard_restricted_entrypoint(root: Path | None = None) -> None:
    """Terminate a forbidden entrypoint before its application imports."""

    if should_block_normal_entrypoint(root):
        emit_fixed_failure(ENTRYPOINT_BLOCKED, 77)


def validate_private_authority_file(path: Path) -> os.stat_result:
    """Stdlib-only minimum validation used by the wrapper before YAML load."""

    try:
        directory = os.lstat(path.parent)
        if (
            stat.S_ISLNK(directory.st_mode)
            or not stat.S_ISDIR(directory.st_mode)
            or stat.S_IMODE(directory.st_mode) != 0o700
            or (hasattr(os, "geteuid") and directory.st_uid != os.geteuid())
        ):
            raise RuntimeError(AUTHORITY_INVALID)
        before = os.lstat(path)
    except OSError as exc:
        raise RuntimeError(AUTHORITY_INVALID) from exc
    if not stat.S_ISREG(before.st_mode) or stat.S_ISLNK(before.st_mode):
        raise RuntimeError(AUTHORITY_INVALID)
    if hasattr(os, "geteuid") and before.st_uid != os.geteuid():
        raise RuntimeError(AUTHORITY_INVALID)
    if stat.S_IMODE(before.st_mode) != 0o600:
        raise RuntimeError(AUTHORITY_INVALID)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
        try:
            opened = os.fstat(fd)
        finally:
            os.close(fd)
    except OSError as exc:
        raise RuntimeError(AUTHORITY_INVALID) from exc
    if (
        before.st_dev != opened.st_dev
        or before.st_ino != opened.st_ino
        or stat.S_IFMT(before.st_mode) != stat.S_IFMT(opened.st_mode)
        or stat.S_IMODE(opened.st_mode) != 0o600
        or (hasattr(os, "geteuid") and opened.st_uid != os.geteuid())
    ):
        raise RuntimeError(AUTHORITY_INVALID)
    return opened


__all__ = [
    "AUTHORITY_INVALID",
    "RestrictedBootstrapScanner",
    "arm_process_authority",
    "authority_artifact_exists",
    "authority_path",
    "config_has_restricted_signal",
    "emit_fixed_failure",
    "guard_restricted_entrypoint",
    "process_authority_is_armed",
    "resolve_global_hermes_root",
    "restricted_directory",
    "root_config_path",
    "validate_private_authority_file",
]
