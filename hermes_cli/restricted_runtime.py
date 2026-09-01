"""Closed text-only Hermes runner for the restricted conversation UDS.

This module is imported only after :mod:`hermes_cli.restricted_entry` has
closed the normal Hermes import path.  It intentionally does not import the
agent, providers, tools, plugins, memory, MCP, UI, or SessionDB.
"""

from __future__ import annotations

import errno
import hashlib
import hmac
import json
import os
import secrets
import socket
import stat
import struct
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, BinaryIO, Mapping

from hermes_cli.restricted_bootstrap import (
    RestrictedConfigSnapshot,
    arm_process_authority,
    authority_artifact_exists,
    authority_path,
    resolve_global_hermes_root,
    restricted_directory,
    read_config_snapshot,
    root_config_path,
)

SOCKET_PATH = Path("/run/restricted-inference/conversation.sock")
RUNTIME_UID = 10006
RUNTIME_GID = 20001
MAX_RESPONSE_BYTES = 1024 * 1024
MAX_INPUT_BYTES = 131072
READINESS_TIMEOUT_SECONDS = 3.0
TURN_TIMEOUT_SECONDS = 40.0

NONCLAIMS = MappingProxyType({
    "deployment_conformant": False,
    "model_attested": False,
    "phi_authorized": False,
})

RESTRICTED_READINESS = MappingProxyType({
    "schema_version": "restricted-conversation-readiness.v1",
    "status": "ready",
    "policy_epoch": "",
    "policy_digest": "",
    "classification": "PHI",
    "system_instruction_version": "restricted-phi-system.v1",
    "allowed_modalities": ["text"],
    "tools_allowed": False,
    "fallbacks": [],
    "max_provider_attempts": 1,
    "streaming": False,
    "max_output_tokens": 4096,
    "max_canonical_input_utf8_bytes": MAX_INPUT_BYTES,
    "response_profile": "restricted-local-text-response.v1",
})


class RestrictedError(RuntimeError):
    exit_code = 78
    symbol = "RESTRICTED_AUTHORITY_INVALID"


class RestrictedUsageError(RestrictedError):
    exit_code = 64
    symbol = "RESTRICTED_USAGE_ERROR"


class RestrictedPlatformError(RestrictedError):
    exit_code = 69
    symbol = "RESTRICTED_PLATFORM_UNSUPPORTED"


class RestrictedTurnFailed(RestrictedError):
    exit_code = 70
    symbol = "RESTRICTED_TURN_FAILED"


class RestrictedRuntimeUnavailable(RestrictedError):
    exit_code = 74
    symbol = "RESTRICTED_RUNTIME_UNAVAILABLE"


class RestrictedPendingError(RestrictedError):
    exit_code = 75
    symbol = "RESTRICTED_PENDING_AMBIGUOUS"


class RestrictedPolicyMismatch(RestrictedError):
    exit_code = 76
    symbol = "RESTRICTED_POLICY_MISMATCH"


class RestrictedEntrypointBlocked(RestrictedError):
    exit_code = 77
    symbol = "RESTRICTED_ENTRYPOINT_BLOCKED"


class RestrictedProtocolError(RestrictedRuntimeUnavailable):
    pass


class RestrictedAuthorityError(RestrictedError):
    pass


@dataclass(frozen=True)
class RestrictedConfig:
    enabled: bool
    expected_policy_epoch: str | None
    expected_policy_digest: str | None


def _closed_json_loads(raw: bytes) -> Any:
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise RestrictedProtocolError() from exc
    if text.startswith("\ufeff"):
        raise RestrictedProtocolError()

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise RestrictedProtocolError()
            result[key] = value
        return result

    try:
        return json.loads(
            text,
            object_pairs_hook=pairs,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                RestrictedProtocolError()
            ),
        )
    except (json.JSONDecodeError, UnicodeError, RecursionError) as exc:
        raise RestrictedProtocolError() from exc


def _closed_json_bytes(value: Mapping[str, Any]) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8", "strict"
        )
    except (UnicodeError, TypeError, ValueError) as exc:
        raise RestrictedUsageError() from exc


class RestrictedYamlConfigLoader:
    """Post-gate YAML loader with one closed root block."""

    _KEYS = {"enabled", "expected_policy_epoch", "expected_policy_digest"}

    def __init__(
        self,
        path: Path,
        *,
        snapshot: RestrictedConfigSnapshot | None = None,
    ):
        self.path = Path(path)
        self.snapshot = (
            snapshot if snapshot is not None else read_config_snapshot(self.path)
        )

    def load(self) -> RestrictedConfig:
        if not self.snapshot.stable:
            raise RestrictedAuthorityError()
        try:
            import yaml
        except Exception as exc:
            raise RestrictedAuthorityError() from exc

        class UniqueKeyLoader(yaml.SafeLoader):
            pass

        def construct_unique_mapping(loader, node, deep=False):
            loader.flatten_mapping(node)
            result = {}
            for key_node, value_node in node.value:
                key = loader.construct_object(key_node, deep=deep)
                try:
                    duplicate = key in result
                except TypeError as exc:
                    raise RestrictedAuthorityError() from exc
                if duplicate:
                    raise RestrictedAuthorityError()
                result[key] = loader.construct_object(value_node, deep=deep)
            return result

        UniqueKeyLoader.add_constructor(
            "tag:yaml.org,2002:map",
            construct_unique_mapping,
        )
        try:
            text = self.snapshot.raw.decode("utf-8", "strict")
            raw = (
                yaml.load(text, Loader=UniqueKeyLoader) if self.snapshot.exists else {}
            )
        except RestrictedError:
            raise
        except Exception as exc:
            raise RestrictedAuthorityError() from exc
        if raw is None:
            raw = {}
        if not isinstance(raw, dict):
            raise RestrictedAuthorityError()
        block = raw.get("restricted_runtime")
        if block is None:
            return RestrictedConfig(False, None, None)
        if not isinstance(block, dict) or set(block) != self._KEYS:
            raise RestrictedAuthorityError()
        enabled = block.get("enabled")
        epoch = block.get("expected_policy_epoch")
        digest = block.get("expected_policy_digest")
        if not isinstance(enabled, bool):
            raise RestrictedAuthorityError()
        if enabled:
            _validate_policy_pair(epoch, digest)
        elif epoch is not None or digest is not None:
            raise RestrictedAuthorityError()
        return RestrictedConfig(enabled, epoch, digest)


def _validate_policy_pair(epoch: Any, digest: Any) -> None:
    if not isinstance(epoch, str) or not epoch or len(epoch.encode("utf-8")) > 256:
        raise RestrictedAuthorityError()
    if not isinstance(digest, str) or len(digest) != 64 or digest.lower() != digest:
        raise RestrictedAuthorityError()
    try:
        int(digest, 16)
    except ValueError as exc:
        raise RestrictedAuthorityError() from exc


def load_root_config(
    root: Path | None = None,
    *,
    snapshot: RestrictedConfigSnapshot | None = None,
) -> RestrictedConfig:
    return RestrictedYamlConfigLoader(root_config_path(root), snapshot=snapshot).load()


def _rewrite_root_restricted_config(
    root: Path, config: RestrictedConfig | None
) -> None:
    try:
        import yaml
    except Exception as exc:
        raise RestrictedAuthorityError() from exc
    path = root_config_path(root)
    try:
        if path.exists():
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        else:
            data = {}
        if not isinstance(data, dict):
            raise RestrictedAuthorityError()
        if config is None:
            data.pop("restricted_runtime", None)
        else:
            data["restricted_runtime"] = {
                "enabled": config.enabled,
                "expected_policy_epoch": config.expected_policy_epoch,
                "expected_policy_digest": config.expected_policy_digest,
            }
        data["_config_version"] = 40
        payload = yaml.safe_dump(data, sort_keys=False, allow_unicode=True).encode(
            "utf-8"
        )
        root.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = _secure_temp(path.parent, ".config-restricted-")
        try:
            with os.fdopen(fd, "wb", closefd=True) as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, path)
            _fsync_directory(path.parent)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise
    except RestrictedError:
        raise
    except Exception as exc:
        raise RestrictedAuthorityError() from exc


def _write_root_restricted_config(root: Path, config: RestrictedConfig) -> None:
    _rewrite_root_restricted_config(root, config)


def _remove_root_restricted_config(root: Path) -> None:
    _rewrite_root_restricted_config(root, None)


def platform_supports_restricted_runtime() -> bool:
    return (
        sys.platform != "win32"
        and hasattr(socket, "AF_UNIX")
        and hasattr(socket, "SO_PEERCRED")
        and hasattr(os, "geteuid")
    )


def _require_supported_platform() -> None:
    if not platform_supports_restricted_runtime():
        raise RestrictedPlatformError()


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
    fd = os.open(path, flags)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _secure_temp(directory: Path, prefix: str) -> tuple[int, str]:
    for _ in range(128):
        name = directory / (prefix + secrets.token_hex(16))
        try:
            fd = os.open(
                name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0),
                0o600,
            )
            return fd, os.fspath(name)
        except FileExistsError:
            continue
    raise RestrictedAuthorityError()


def _ensure_private_directory(path: Path, *, create: bool) -> os.stat_result:
    if create:
        try:
            path.mkdir(mode=0o700, parents=False, exist_ok=False)
            _fsync_directory(path.parent)
        except FileExistsError:
            pass
        except Exception as exc:
            raise RestrictedAuthorityError() from exc
    try:
        info = os.lstat(path)
    except OSError as exc:
        raise RestrictedAuthorityError() from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise RestrictedAuthorityError()
    if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise RestrictedAuthorityError()
    return info


def _validate_open_private_file(path: Path, fd: int) -> None:
    before = os.lstat(path)
    opened = os.fstat(fd)
    if (
        stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_uid != os.geteuid()
        or stat.S_IMODE(before.st_mode) != 0o600
        or opened.st_dev != before.st_dev
        or opened.st_ino != before.st_ino
        or not stat.S_ISREG(opened.st_mode)
        or opened.st_uid != os.geteuid()
        or stat.S_IMODE(opened.st_mode) != 0o600
    ):
        raise RestrictedAuthorityError()


def _open_private_file(path: Path, flags: int) -> int:
    try:
        fd = os.open(
            path,
            flags | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
        )
        try:
            _validate_open_private_file(path, fd)
        except Exception:
            os.close(fd)
            raise
        return fd
    except RestrictedError:
        raise
    except OSError as exc:
        raise RestrictedAuthorityError() from exc


def _read_private_file(path: Path, *, expected_size: int | None = None) -> bytes:
    fd = _open_private_file(path, os.O_RDONLY)
    try:
        chunks = []
        total = 0
        while True:
            block = os.read(fd, 64 * 1024)
            if not block:
                break
            total += len(block)
            if total > MAX_RESPONSE_BYTES:
                raise RestrictedAuthorityError()
            chunks.append(block)
    finally:
        os.close(fd)
    payload = b"".join(chunks)
    if expected_size is not None and len(payload) != expected_size:
        raise RestrictedAuthorityError()
    return payload


def _atomic_private_write(directory: Path, path: Path, payload: bytes) -> None:
    _ensure_private_directory(directory, create=False)
    if os.path.lexists(path):
        _read_private_file(path)
    fd, tmp_name = _secure_temp(directory, ".restricted-")
    try:
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
        _read_private_file(path)
        _fsync_directory(directory)
    except Exception as exc:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        if isinstance(exc, RestrictedError):
            raise
        raise RestrictedAuthorityError() from exc


_SESSION_KEYS = {
    "schema_version",
    "policy_epoch",
    "policy_digest",
    "conversation_id",
    "conversation_epoch",
    "hmac_key_fingerprint_sha256",
    "pending_request_id",
    "pending_message_hmac_sha256",
}


class RestrictedStateStore:
    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root is not None else resolve_global_hermes_root()
        self.directory = restricted_directory(self.root)
        self.enabled_path = authority_path(self.root)
        self.session_path = self.directory / "session.json"
        self.key_path = self.directory / "message-hmac.key"
        self.lock_path = self.directory / "runner.lock"

    def ensure_directory(self) -> None:
        _require_supported_platform()
        self.root.mkdir(parents=True, exist_ok=True)
        _ensure_private_directory(self.directory, create=True)

    def initialize(self, policy_epoch: str, policy_digest: str) -> None:
        self.ensure_directory()
        if os.path.lexists(self.key_path):
            key = _read_private_file(self.key_path, expected_size=32)
        else:
            key = secrets.token_bytes(32)
            _atomic_private_write(self.directory, self.key_path, key)
        fingerprint = hashlib.sha256(key).hexdigest()
        if os.path.lexists(self.session_path):
            existing = self.read_state()
            if (
                existing["policy_epoch"] != policy_epoch
                or existing["policy_digest"] != policy_digest
                or existing["pending_request_id"] is not None
            ):
                raise RestrictedAuthorityError()
            existing["conversation_id"] = str(uuid.uuid4())
            existing["conversation_epoch"] = None
            self.write_state(existing)
            return
        state = {
            "schema_version": "restricted-hermes-session.v1",
            "policy_epoch": policy_epoch,
            "policy_digest": policy_digest,
            "conversation_id": str(uuid.uuid4()),
            "conversation_epoch": None,
            "hmac_key_fingerprint_sha256": fingerprint,
            "pending_request_id": None,
            "pending_message_hmac_sha256": None,
        }
        self.write_state(state)

    def write_authority(self, policy_epoch: str, policy_digest: str) -> None:
        payload = _closed_json_bytes({
            "schema_version": "restricted-hermes-authority.v1",
            "policy_epoch": policy_epoch,
            "policy_digest": policy_digest,
        })
        _atomic_private_write(self.directory, self.enabled_path, payload)

    def read_authority(self) -> dict[str, Any]:
        payload = _read_private_file(self.enabled_path)
        data = _closed_json_loads(payload)
        if not isinstance(data, dict) or set(data) != {
            "schema_version",
            "policy_epoch",
            "policy_digest",
        }:
            raise RestrictedAuthorityError()
        if data["schema_version"] != "restricted-hermes-authority.v1":
            raise RestrictedAuthorityError()
        if not isinstance(data["policy_epoch"], str) or not isinstance(
            data["policy_digest"], str
        ):
            raise RestrictedAuthorityError()
        return data

    def remove_authority(self) -> None:
        _ensure_private_directory(self.directory, create=False)
        _read_private_file(self.enabled_path)
        try:
            os.unlink(self.enabled_path)
            _fsync_directory(self.directory)
        except OSError as exc:
            raise RestrictedAuthorityError() from exc

    def read_state(self) -> dict[str, Any]:
        _ensure_private_directory(self.directory, create=False)
        payload = _read_private_file(self.session_path)
        data = _closed_json_loads(payload)
        if not isinstance(data, dict) or set(data) != _SESSION_KEYS:
            raise RestrictedAuthorityError()
        if data["schema_version"] != "restricted-hermes-session.v1":
            raise RestrictedAuthorityError()
        for name in (
            "policy_epoch",
            "policy_digest",
            "conversation_id",
            "hmac_key_fingerprint_sha256",
        ):
            if not isinstance(data[name], str) or not data[name]:
                raise RestrictedAuthorityError()
        try:
            uuid.UUID(data["conversation_id"])
        except (ValueError, AttributeError) as exc:
            raise RestrictedAuthorityError() from exc
        for name in (
            "conversation_epoch",
            "pending_request_id",
            "pending_message_hmac_sha256",
        ):
            if data[name] is not None and not isinstance(data[name], str):
                raise RestrictedAuthorityError()
        if (data["pending_request_id"] is None) != (
            data["pending_message_hmac_sha256"] is None
        ):
            raise RestrictedAuthorityError()
        key = _read_private_file(self.key_path, expected_size=32)
        if not hmac.compare_digest(
            hashlib.sha256(key).hexdigest(), data["hmac_key_fingerprint_sha256"]
        ):
            raise RestrictedAuthorityError()
        return data

    def write_state(self, state: Mapping[str, Any]) -> None:
        if set(state) != _SESSION_KEYS:
            raise RestrictedAuthorityError()
        _atomic_private_write(
            self.directory, self.session_path, _closed_json_bytes(dict(state))
        )

    def persist_pending(self, message: str, request_id: str | None = None) -> str:
        if (
            not isinstance(message, str)
            or not message
            or len(message.encode("utf-8", "strict")) > MAX_INPUT_BYTES
        ):
            raise RestrictedUsageError()
        state = self.read_state()
        key = _read_private_file(self.key_path, expected_size=32)
        digest = hmac.new(
            key, message.encode("utf-8", "strict"), hashlib.sha256
        ).hexdigest()
        if state["pending_request_id"] is not None:
            if not hmac.compare_digest(state["pending_message_hmac_sha256"], digest):
                raise RestrictedPendingError()
            return state["pending_request_id"]
        actual_id = request_id or str(uuid.uuid4())
        try:
            uuid.UUID(actual_id)
        except (ValueError, AttributeError) as exc:
            raise RestrictedAuthorityError() from exc
        state["pending_request_id"] = actual_id
        state["pending_message_hmac_sha256"] = digest
        self.write_state(state)
        return actual_id

    def clear_pending(self) -> None:
        state = self.read_state()
        state["pending_request_id"] = None
        state["pending_message_hmac_sha256"] = None
        self.write_state(state)

    def set_conversation_epoch(self, epoch: str) -> None:
        if not isinstance(epoch, str) or not epoch:
            raise RestrictedProtocolError()
        state = self.read_state()
        state["conversation_epoch"] = epoch
        self.write_state(state)

    def new_conversation(self, *, confirm_abandon_pending: bool = False) -> None:
        state = self.read_state()
        if state["pending_request_id"] is not None and not confirm_abandon_pending:
            raise RestrictedPendingError()
        state["conversation_id"] = str(uuid.uuid4())
        state["conversation_epoch"] = None
        state["pending_request_id"] = None
        state["pending_message_hmac_sha256"] = None
        self.write_state(state)

    def acquire_runner_lock(self):
        _require_supported_platform()
        self.ensure_directory()
        fd = -1
        try:
            import fcntl

            flags = (
                os.O_RDWR
                | os.O_CREAT
                | os.O_EXCL
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_NOFOLLOW", 0)
            )
            try:
                fd = os.open(self.lock_path, flags, 0o600)
                _validate_open_private_file(self.lock_path, fd)
                os.fsync(fd)
                _fsync_directory(self.directory)
            except FileExistsError:
                fd = _open_private_file(self.lock_path, os.O_RDWR)
            if os.fstat(fd).st_size != 0:
                raise RestrictedAuthorityError()
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except RestrictedError:
            if fd >= 0:
                os.close(fd)
            raise
        except (ImportError, OSError) as exc:
            if fd >= 0:
                os.close(fd)
            raise RestrictedAuthorityError() from exc
        return _RunnerLock(fd)


class _RunnerLock:
    def __init__(self, fd: int):
        self.fd = fd

    def close(self) -> None:
        if self.fd >= 0:
            try:
                import fcntl

                fcntl.flock(self.fd, fcntl.LOCK_UN)
            finally:
                os.close(self.fd)
                self.fd = -1

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


def _socket_identity(
    path: Path, expected_uid: int, expected_gid: int
) -> os.stat_result:
    try:
        info = os.lstat(path)
    except OSError as exc:
        raise RestrictedRuntimeUnavailable() from exc
    if (
        stat.S_ISLNK(info.st_mode)
        or not stat.S_ISSOCK(info.st_mode)
        or info.st_uid != expected_uid
        or info.st_gid != expected_gid
        or stat.S_IMODE(info.st_mode) != 0o660
    ):
        raise RestrictedRuntimeUnavailable()
    return info


class RestrictedUdsClient:
    def __init__(
        self,
        *,
        socket_path: Path = SOCKET_PATH,
        expected_uid: int = RUNTIME_UID,
        expected_gid: int = RUNTIME_GID,
    ):
        self.socket_path = Path(socket_path)
        self.expected_uid = expected_uid
        self.expected_gid = expected_gid

    def _connect(self, deadline: float) -> socket.socket:
        _require_supported_platform()
        before = _socket_identity(
            self.socket_path, self.expected_uid, self.expected_gid
        )
        sock = None
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RestrictedRuntimeUnavailable()
            sock.settimeout(remaining)
            sock.connect(os.fspath(self.socket_path))
            raw = sock.getsockopt(
                socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")
            )
            pid, uid, gid = struct.unpack("3i", raw)
            if pid < 0 or uid != self.expected_uid or gid != self.expected_gid:
                raise RestrictedRuntimeUnavailable()
            after = _socket_identity(
                self.socket_path, self.expected_uid, self.expected_gid
            )
            if before.st_dev != after.st_dev or before.st_ino != after.st_ino:
                raise RestrictedRuntimeUnavailable()
            return sock
        except RestrictedError:
            if sock is not None:
                sock.close()
            raise
        except Exception as exc:
            if sock is not None:
                sock.close()
            raise RestrictedRuntimeUnavailable() from exc

    def _request(
        self,
        method: str,
        target: str,
        body: bytes,
        timeout: float,
        *,
        ambiguous_after_send: bool = False,
    ):
        deadline = time.monotonic() + timeout
        sock = self._connect(deadline)
        sent = False
        try:
            request = (
                f"{method} {target} HTTP/1.1\r\n"
                "Host: localhost\r\n"
                "Content-Type: application/json\r\n"
                "Connection: close\r\n"
                f"Content-Length: {len(body)}\r\n\r\n"
            ).encode("ascii") + body
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RestrictedRuntimeUnavailable()
            sock.settimeout(remaining)
            sock.sendall(request)
            sent = True
            chunks = []
            total = 0
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError()
                sock.settimeout(remaining)
                block = sock.recv(64 * 1024)
                if not block:
                    break
                total += len(block)
                if total > MAX_RESPONSE_BYTES + 64 * 1024:
                    raise RestrictedProtocolError()
                chunks.append(block)
        except RestrictedError:
            raise
        except Exception as exc:
            if sent and ambiguous_after_send:
                raise RestrictedPendingError() from exc
            raise RestrictedRuntimeUnavailable() from exc
        finally:
            sock.close()
        try:
            return _parse_http_response(b"".join(chunks))
        except RestrictedProtocolError as exc:
            if ambiguous_after_send:
                raise RestrictedPendingError() from exc
            raise

    def ready(self, policy_epoch: str, policy_digest: str) -> dict[str, Any]:
        data = self._request("GET", "/readyz", b"", READINESS_TIMEOUT_SECONDS)
        expected = dict(
            RESTRICTED_READINESS, policy_epoch=policy_epoch, policy_digest=policy_digest
        )
        if data != expected:
            raise RestrictedPolicyMismatch()
        return data

    def create_conversation(self, conversation_id: str) -> str:
        data = self._request(
            "POST",
            f"/v1/restricted/conversations/{conversation_id}",
            b"",
            READINESS_TIMEOUT_SECONDS,
        )
        if not isinstance(data, dict) or set(data) != {
            "schema_version",
            "conversation_id",
            "conversation_epoch",
        }:
            raise RestrictedProtocolError()
        if (
            data["schema_version"] != "restricted-conversation.v1"
            or data["conversation_id"] != conversation_id
        ):
            raise RestrictedProtocolError()
        if (
            not isinstance(data["conversation_epoch"], str)
            or not data["conversation_epoch"]
        ):
            raise RestrictedProtocolError()
        return data["conversation_epoch"]

    def turn(self, conversation_id: str, request: Mapping[str, Any]) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/v1/restricted/conversations/{conversation_id}/turns",
            _closed_json_bytes(dict(request)),
            TURN_TIMEOUT_SECONDS,
            ambiguous_after_send=True,
        )


def _parse_http_response(raw: bytes) -> Any:
    marker = raw.find(b"\r\n\r\n")
    if marker < 0 or marker > 64 * 1024:
        raise RestrictedProtocolError()
    header_raw = raw[:marker]
    body = raw[marker + 4 :]
    try:
        lines = header_raw.decode("ascii", "strict").split("\r\n")
    except UnicodeDecodeError as exc:
        raise RestrictedProtocolError() from exc
    if lines[0] != "HTTP/1.1 200 OK":
        raise RestrictedProtocolError()
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if not line or ":" not in line:
            raise RestrictedProtocolError()
        name, value = line.split(":", 1)
        lowered = name.strip().lower()
        if lowered in headers:
            raise RestrictedProtocolError()
        headers[lowered] = value.strip()
    required_headers = {"content-type", "content-length", "connection"}
    if not required_headers.issubset(headers):
        raise RestrictedProtocolError()
    if "transfer-encoding" in headers or "content-encoding" in headers:
        raise RestrictedProtocolError()
    if (
        headers["content-type"] != "application/json"
        or headers["connection"].lower() != "close"
    ):
        raise RestrictedProtocolError()
    try:
        length = int(headers["content-length"])
    except ValueError as exc:
        raise RestrictedProtocolError() from exc
    if length < 0 or length > MAX_RESPONSE_BYTES or len(body) != length:
        raise RestrictedProtocolError()
    return _closed_json_loads(body)


def validate_turn_result(data: Any, expected_epoch: str) -> tuple[str, str | None]:
    if not isinstance(data, dict):
        raise RestrictedProtocolError()
    status = data.get("status")
    if status == "COMMITTED":
        expected = {
            "schema_version",
            "turn_id",
            "conversation_epoch",
            "status",
            "message",
        }
        if (
            set(data) != expected
            or data.get("schema_version") != "restricted-turn-result.v1"
        ):
            raise RestrictedProtocolError()
        if not isinstance(data.get("message"), str):
            raise RestrictedProtocolError()
    else:
        expected = {"schema_version", "turn_id", "conversation_epoch", "status"}
        if (
            set(data) != expected
            or data.get("schema_version") != "restricted-turn-status.v1"
        ):
            raise RestrictedProtocolError()
    try:
        uuid.UUID(data["turn_id"])
    except (ValueError, TypeError, AttributeError) as exc:
        raise RestrictedProtocolError() from exc
    if data.get("conversation_epoch") != expected_epoch:
        raise RestrictedProtocolError()
    if status not in {
        "COMMITTED",
        "REJECTED",
        "FAILED",
        "INDETERMINATE",
        "RECEIVED",
        "REQUEST_COMMITTED",
        "INFERENCE_PENDING",
        "RESPONSE_RECEIVED",
    }:
        raise RestrictedProtocolError()
    return status, data.get("message")


class RestrictedRunner:
    def __init__(
        self, root: Path | None = None, client: RestrictedUdsClient | None = None
    ):
        self.root = Path(root) if root is not None else resolve_global_hermes_root()
        self.config = load_root_config(self.root)
        self.store = RestrictedStateStore(self.root)
        self.client = client or RestrictedUdsClient()
        self.lock = None
        self.application_restricted = False

    def start(self) -> None:
        _require_supported_platform()
        if not self.config.enabled or not authority_artifact_exists(self.root):
            raise RestrictedAuthorityError()
        authority = self.store.read_authority()
        if (
            authority["policy_epoch"] != self.config.expected_policy_epoch
            or authority["policy_digest"] != self.config.expected_policy_digest
        ):
            raise RestrictedAuthorityError()
        arm_process_authority(self.root)
        self.lock = self.store.acquire_runner_lock()
        try:
            self.client.ready(
                self.config.expected_policy_epoch, self.config.expected_policy_digest
            )
            state = self.store.read_state()
            if (
                state["policy_epoch"] != self.config.expected_policy_epoch
                or state["policy_digest"] != self.config.expected_policy_digest
            ):
                raise RestrictedPolicyMismatch()
            if state["conversation_epoch"] is None:
                epoch = self.client.create_conversation(state["conversation_id"])
                self.store.set_conversation_epoch(epoch)
            self.application_restricted = True
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        self.application_restricted = False
        if self.lock is not None:
            self.lock.close()
            self.lock = None

    def status_payload(self) -> dict[str, bool]:
        return {
            "application_restricted": self.application_restricted,
            **NONCLAIMS,
        }

    def submit(self, message: str) -> str:
        if not self.application_restricted:
            raise RestrictedAuthorityError()
        state = self.store.read_state()
        request_id = self.store.persist_pending(message)
        request = {
            "schema_version": "restricted-turn.v1",
            "client_request_id": request_id,
            "conversation_epoch": state["conversation_epoch"],
            "message": message,
        }
        try:
            data = self.client.turn(state["conversation_id"], request)
            status, response = validate_turn_result(data, state["conversation_epoch"])
        except RestrictedPendingError:
            raise
        except Exception as exc:
            raise RestrictedPendingError() from exc
        if status == "COMMITTED":
            self.store.clear_pending()
            return response or ""
        if status in {"REJECTED", "FAILED"}:
            self.store.clear_pending()
            raise RestrictedTurnFailed()
        raise RestrictedPendingError()

    def new(self, *, confirm_abandon_pending: bool = False) -> None:
        self.store.new_conversation(confirm_abandon_pending=confirm_abandon_pending)
        state = self.store.read_state()
        epoch = self.client.create_conversation(state["conversation_id"])
        self.store.set_conversation_epoch(epoch)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_args):
        self.close()


def validate_stdin_invocation(argv: list[str], *, stdin_isatty: bool) -> None:
    if argv != ["--stdin"] or stdin_isatty:
        raise RestrictedUsageError()


def _status(root: Path) -> dict[str, bool]:
    configured = False
    armed = authority_artifact_exists(root)
    pending = False
    try:
        config = load_root_config(root)
        configured = config.enabled
    except RestrictedError:
        pass
    try:
        if armed:
            state = RestrictedStateStore(root).read_state()
            pending = state["pending_request_id"] is not None
    except RestrictedError:
        pass
    runner_lock_held = False
    runtime_reachable = False
    policy_bound = False
    if armed and platform_supports_restricted_runtime():
        try:
            store = RestrictedStateStore(root)
            if os.path.lexists(store.lock_path):
                import fcntl

                fd = _open_private_file(store.lock_path, os.O_RDWR)
                if os.fstat(fd).st_size != 0:
                    raise RestrictedAuthorityError()
                try:
                    try:
                        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        fcntl.flock(fd, fcntl.LOCK_UN)
                    except OSError as exc:
                        if exc.errno in {errno.EACCES, errno.EAGAIN}:
                            runner_lock_held = True
                        else:
                            raise
                finally:
                    os.close(fd)
        except Exception:
            runner_lock_held = False
        if configured:
            try:
                RestrictedUdsClient().ready(
                    config.expected_policy_epoch, config.expected_policy_digest
                )
                runtime_reachable = True
                policy_bound = True
            except RestrictedPolicyMismatch:
                runtime_reachable = True
            except RestrictedError:
                pass
    return {
        "configured": configured,
        "armed": armed,
        "runtime_reachable": runtime_reachable,
        "policy_bound": policy_bound,
        "runner_lock_held": runner_lock_held,
        "active_process": runner_lock_held,
        "application_restricted": False,
        "pending_turn": pending,
        **NONCLAIMS,
    }


def restricted_status(root: Path | None = None) -> dict[str, bool]:
    actual_root = Path(root) if root is not None else resolve_global_hermes_root()
    return _status(actual_root)


def restricted_doctor(
    root: Path | None = None,
    *,
    expected_policy_epoch: str | None = None,
    expected_policy_digest: str | None = None,
    client: RestrictedUdsClient | None = None,
) -> dict[str, bool]:
    _require_supported_platform()
    actual_root = Path(root) if root is not None else resolve_global_hermes_root()
    config = load_root_config(actual_root)
    epoch = expected_policy_epoch or config.expected_policy_epoch
    digest = expected_policy_digest or config.expected_policy_digest
    if (not epoch or not digest) and authority_artifact_exists(actual_root):
        authority = RestrictedStateStore(actual_root).read_authority()
        epoch = authority["policy_epoch"]
        digest = authority["policy_digest"]
    if not epoch or not digest:
        raise RestrictedAuthorityError()
    (client or RestrictedUdsClient()).ready(epoch, digest)
    return {
        "runtime_reachable": True,
        "policy_bound": True,
        "application_restricted": False,
        **NONCLAIMS,
    }


def restricted_enable(
    policy_epoch: str,
    policy_digest: str,
    *,
    confirm_stopped: bool,
    root: Path | None = None,
    client: RestrictedUdsClient | None = None,
) -> None:
    if not confirm_stopped:
        raise RestrictedUsageError()
    _validate_policy_pair(policy_epoch, policy_digest)
    actual_root = Path(root) if root is not None else resolve_global_hermes_root()
    restricted_doctor(
        actual_root,
        expected_policy_epoch=policy_epoch,
        expected_policy_digest=policy_digest,
        client=client,
    )
    store = RestrictedStateStore(actual_root)
    current = load_root_config(actual_root)
    if authority_artifact_exists(actual_root):
        authority = store.read_authority()
        if not current.enabled:
            raise RestrictedAuthorityError()
        if (
            authority["policy_epoch"] != policy_epoch
            or authority["policy_digest"] != policy_digest
        ):
            raise RestrictedAuthorityError()
        return
    if current.enabled:
        raise RestrictedAuthorityError()
    store.initialize(policy_epoch, policy_digest)
    store.write_authority(policy_epoch, policy_digest)
    _write_root_restricted_config(
        actual_root, RestrictedConfig(True, policy_epoch, policy_digest)
    )


def restricted_disable(root: Path | None = None) -> None:
    actual_root = Path(root) if root is not None else resolve_global_hermes_root()
    store = RestrictedStateStore(actual_root)
    if not authority_artifact_exists(actual_root):
        config = load_root_config(actual_root)
        if config.enabled:
            raise RestrictedAuthorityError()
        return
    state = store.read_state()
    if state["pending_request_id"] is not None:
        raise RestrictedPendingError()
    _remove_root_restricted_config(actual_root)
    store.remove_authority()


def run_one_shot(
    stdin: BinaryIO,
    *,
    root: Path | None = None,
    client: RestrictedUdsClient | None = None,
) -> str:
    raw = stdin.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise RestrictedUsageError()
    try:
        message = raw.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise RestrictedUsageError() from exc
    if not message:
        raise RestrictedUsageError()
    with RestrictedRunner(root, client) as runner:
        return runner.submit(message)


def run_repl(
    *, root: Path | None = None, client: RestrictedUdsClient | None = None
) -> None:
    with RestrictedRunner(root, client) as runner:
        while True:
            try:
                message = input("restricted> ")
            except EOFError:
                return
            if message == "/exit":
                return
            if message == "/status":
                print(
                    json.dumps(
                        runner.status_payload(), sort_keys=True, separators=(",", ":")
                    )
                )
                continue
            if message.startswith("/new"):
                if message == "/new":
                    runner.new()
                elif message == "/new --confirm-abandon-pending":
                    runner.new(confirm_abandon_pending=True)
                else:
                    raise RestrictedUsageError()
                continue
            if message.startswith("/"):
                raise RestrictedUsageError()
            print(runner.submit(message))


def emit_restricted_error(error: RestrictedError) -> None:
    sys.stderr.write(error.symbol + "\n")
    sys.stderr.flush()


__all__ = [
    "NONCLAIMS",
    "RESTRICTED_READINESS",
    "RestrictedAuthorityError",
    "RestrictedConfig",
    "RestrictedError",
    "RestrictedEntrypointBlocked",
    "RestrictedPendingError",
    "RestrictedPlatformError",
    "RestrictedPolicyMismatch",
    "RestrictedProtocolError",
    "RestrictedRunner",
    "RestrictedRuntimeUnavailable",
    "RestrictedStateStore",
    "RestrictedTurnFailed",
    "RestrictedUdsClient",
    "RestrictedUsageError",
    "RestrictedYamlConfigLoader",
    "emit_restricted_error",
    "load_root_config",
    "platform_supports_restricted_runtime",
    "restricted_disable",
    "restricted_doctor",
    "restricted_enable",
    "restricted_status",
    "run_one_shot",
    "run_repl",
    "validate_stdin_invocation",
    "validate_turn_result",
]
