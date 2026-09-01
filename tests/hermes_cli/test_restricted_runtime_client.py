import json
import os
import socket
import threading
import tempfile
import uuid
from pathlib import Path

import pytest


EPOCH = "policy-2026-08-31"
DIGEST = "b" * 64


def _http_response(body):
    payload = json.dumps(body, separators=(",", ":")).encode()
    return (
        b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: "
        + str(len(payload)).encode()
        + b"\r\nConnection: close\r\n\r\n"
        + payload
    )


def _short_socket_path() -> Path:
    # Linux sockaddr_un.sun_path is normally only 108 bytes.  The repository's
    # isolated tmp_path root can exceed that before the test suffix is added.
    return Path(tempfile.mkdtemp(prefix="hrr-", dir="/tmp")) / "c.sock"


@pytest.mark.linux_only
def test_client_authenticates_each_connection_and_binds_readiness():
    from hermes_cli.restricted_runtime import RESTRICTED_READINESS, RestrictedUdsClient

    path = _short_socket_path()
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(path))
    os.chmod(path, 0o660)
    server.listen(1)
    ready = dict(RESTRICTED_READINESS, policy_epoch=EPOCH, policy_digest=DIGEST)

    def serve():
        conn, _ = server.accept()
        with conn:
            conn.recv(65536)
            conn.sendall(_http_response(ready))
        server.close()

    thread = threading.Thread(target=serve)
    thread.start()
    client = RestrictedUdsClient(
        socket_path=path,
        expected_uid=os.geteuid(),
        expected_gid=os.getegid(),
    )
    assert client.ready(EPOCH, DIGEST) == ready
    thread.join(timeout=2)
    path.unlink()
    path.parent.rmdir()


def test_turn_result_schema_is_closed(tmp_path):
    from hermes_cli.restricted_runtime import (
        RestrictedProtocolError,
        validate_turn_result,
    )

    turn_id = str(uuid.uuid4())
    with pytest.raises(RestrictedProtocolError):
        validate_turn_result(
            {
                "schema_version": "restricted-turn-result.v1",
                "turn_id": turn_id,
                "conversation_epoch": "e1",
                "status": "COMMITTED",
                "message": "ok",
                "extra": True,
            },
            "e1",
        )


def test_readiness_rejects_policy_capability_and_unknown_field_mismatch(monkeypatch):
    from hermes_cli.restricted_runtime import (
        RESTRICTED_READINESS,
        RestrictedPolicyMismatch,
        RestrictedUdsClient,
    )

    expected = dict(RESTRICTED_READINESS, policy_epoch=EPOCH, policy_digest=DIGEST)
    client = RestrictedUdsClient()
    for mutation in (
        {**expected, "policy_digest": "0" * 64},
        {**expected, "tools_allowed": True},
        {**expected, "unexpected": False},
    ):
        monkeypatch.setattr(
            client, "_request", lambda *_args, value=mutation, **_kwargs: value
        )
        with pytest.raises(RestrictedPolicyMismatch):
            client.ready(EPOCH, DIGEST)


def test_http_rejects_chunked_duplicate_or_partial_responses():
    from hermes_cli.restricted_runtime import (
        RestrictedProtocolError,
        _parse_http_response,
    )

    invalid = [
        b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 2\r\nContent-Length: 2\r\nConnection: close\r\n\r\n{}",
        b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nTransfer-Encoding: chunked\r\nConnection: close\r\n\r\n0\r\n\r\n",
        b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 10\r\nConnection: close\r\n\r\n{}",
    ]
    for response in invalid:
        with pytest.raises(RestrictedProtocolError):
            _parse_http_response(response)


def test_http_accepts_standard_server_metadata_headers():
    from hermes_cli.restricted_runtime import _parse_http_response

    response = (
        b"HTTP/1.1 200 OK\r\n"
        b"Date: Mon, 31 Aug 2026 12:00:00 GMT\r\n"
        b"Server: uvicorn\r\n"
        b"Content-Type: application/json\r\n"
        b"Content-Length: 2\r\n"
        b"Connection: close\r\n\r\n{}"
    )
    assert _parse_http_response(response) == {}


@pytest.mark.linux_only
def test_wrong_path_owner_contract_fails_before_http_bytes():
    from hermes_cli.restricted_runtime import (
        RestrictedRuntimeUnavailable,
        RestrictedUdsClient,
    )

    path = _short_socket_path()
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(path))
    os.chmod(path, 0o660)
    server.listen(1)
    client = RestrictedUdsClient(
        socket_path=path,
        expected_uid=os.geteuid() + 1,
        expected_gid=os.getegid(),
    )
    with pytest.raises(RestrictedRuntimeUnavailable):
        client.ready(EPOCH, DIGEST)
    server.close()
    path.unlink()
    path.parent.rmdir()


@pytest.mark.linux_only
def test_connect_failures_are_runtime_unavailable_and_preserve_restricted_errors(
    tmp_path, monkeypatch
):
    import hermes_cli.restricted_runtime as restricted

    path = tmp_path / "stale.sock"
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listener.bind(str(path))
    os.chmod(path, 0o660)
    listener.close()
    client = restricted.RestrictedUdsClient(
        socket_path=path,
        expected_uid=os.geteuid(),
        expected_gid=os.getegid(),
    )
    with pytest.raises(restricted.RestrictedRuntimeUnavailable):
        client._connect(__import__("time").monotonic() + 1)

    monkeypatch.setattr(
        restricted,
        "_socket_identity",
        lambda *_args: (_ for _ in ()).throw(restricted.RestrictedPolicyMismatch()),
    )
    with pytest.raises(restricted.RestrictedPolicyMismatch):
        client._connect(__import__("time").monotonic() + 1)


@pytest.mark.linux_only
def test_peer_credential_read_failure_is_runtime_unavailable(tmp_path, monkeypatch):
    import hermes_cli.restricted_runtime as restricted

    path = tmp_path / "peer.sock"
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listener.bind(str(path))
    os.chmod(path, 0o660)

    monkeypatch.setattr(
        restricted.socket,
        "socket",
        lambda *_args: (_ for _ in ()).throw(OSError("synthetic socket failure")),
    )
    client = restricted.RestrictedUdsClient(
        socket_path=path,
        expected_uid=os.geteuid(),
        expected_gid=os.getegid(),
    )
    with pytest.raises(restricted.RestrictedRuntimeUnavailable):
        client._connect(__import__("time").monotonic() + 1)

    class PeerFailureSocket:
        def settimeout(self, _timeout):
            pass

        def connect(self, _path):
            pass

        def getsockopt(self, *_args):
            raise OSError("synthetic SO_PEERCRED failure")

        def close(self):
            pass

    monkeypatch.setattr(restricted.socket, "socket", lambda *_args: PeerFailureSocket())
    with pytest.raises(restricted.RestrictedRuntimeUnavailable):
        client._connect(__import__("time").monotonic() + 1)
    listener.close()


@pytest.mark.linux_only
@pytest.mark.parametrize(
    ("pid", "uid", "gid", "accepted"),
    [
        (0, 10006, 20001, True),
        (4321, 10006, 20001, True),
        (-1, 10006, 20001, False),
        (-(2**31), 10006, 20001, False),
        (0, 10007, 20001, False),
        (0, 10006, 20002, False),
    ],
)
def test_peer_credentials_accept_nonnegative_pid_only_with_exact_identity(
    monkeypatch, pid, uid, gid, accepted
):
    import struct
    import time
    from types import SimpleNamespace

    import hermes_cli.restricted_runtime as restricted

    identity = SimpleNamespace(st_dev=11, st_ino=22)
    monkeypatch.setattr(restricted, "_socket_identity", lambda *_args: identity)

    class PeerSocket:
        closed = False

        def settimeout(self, _timeout):
            pass

        def connect(self, _path):
            pass

        def getsockopt(self, *_args):
            return struct.pack("3i", pid, uid, gid)

        def close(self):
            self.closed = True

    peer = PeerSocket()
    monkeypatch.setattr(restricted.socket, "socket", lambda *_args: peer)
    client = restricted.RestrictedUdsClient(
        expected_uid=restricted.RUNTIME_UID,
        expected_gid=restricted.RUNTIME_GID,
    )

    if accepted:
        assert client._connect(time.monotonic() + 1) is peer
        assert peer.closed is False
    else:
        with pytest.raises(restricted.RestrictedRuntimeUnavailable) as raised:
            client._connect(time.monotonic() + 1)
        assert raised.value.exit_code == 74
        assert peer.closed is True


@pytest.mark.linux_only
@pytest.mark.parametrize("peer_result", [b"\0" * 11, OSError("peer read failed")])
def test_truncated_or_failed_peer_credentials_fail_with_74(monkeypatch, peer_result):
    import time
    from types import SimpleNamespace

    import hermes_cli.restricted_runtime as restricted

    identity = SimpleNamespace(st_dev=11, st_ino=22)
    monkeypatch.setattr(restricted, "_socket_identity", lambda *_args: identity)

    class PeerSocket:
        def settimeout(self, _timeout):
            pass

        def connect(self, _path):
            pass

        def getsockopt(self, *_args):
            if isinstance(peer_result, Exception):
                raise peer_result
            return peer_result

        def close(self):
            pass

    monkeypatch.setattr(restricted.socket, "socket", lambda *_args: PeerSocket())
    client = restricted.RestrictedUdsClient(
        expected_uid=restricted.RUNTIME_UID,
        expected_gid=restricted.RUNTIME_GID,
    )

    with pytest.raises(restricted.RestrictedRuntimeUnavailable) as raised:
        client._connect(time.monotonic() + 1)
    assert raised.value.exit_code == 74


@pytest.mark.linux_only
def test_socket_path_rejects_wrong_mode_type_and_symlink(tmp_path):
    from hermes_cli.restricted_runtime import (
        RestrictedRuntimeUnavailable,
        _socket_identity,
    )

    expected_uid = os.geteuid()
    expected_gid = os.getegid()
    regular = tmp_path / "regular"
    regular.write_bytes(b"")
    os.chmod(regular, 0o660)
    with pytest.raises(RestrictedRuntimeUnavailable):
        _socket_identity(regular, expected_uid, expected_gid)

    socket_path = tmp_path / "real.sock"
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(socket_path))
    os.chmod(socket_path, 0o600)
    with pytest.raises(RestrictedRuntimeUnavailable):
        _socket_identity(socket_path, expected_uid, expected_gid)

    os.chmod(socket_path, 0o660)
    link = tmp_path / "linked.sock"
    link.symlink_to(socket_path)
    with pytest.raises(RestrictedRuntimeUnavailable):
        _socket_identity(link, expected_uid, expected_gid)
    server.close()


@pytest.mark.linux_only
def test_runner_clears_terminal_pending_and_preserves_indeterminate(tmp_path):
    from hermes_cli.restricted_runtime import (
        RestrictedConfig,
        RestrictedPendingError,
        RESTRICTED_READINESS,
        RestrictedRunner,
        RestrictedStateStore,
        _write_root_restricted_config,
    )

    class Client:
        def __init__(self):
            self.status = "COMMITTED"

        def ready(self, epoch, digest):
            return dict(RESTRICTED_READINESS, policy_epoch=epoch, policy_digest=digest)

        def create_conversation(self, _conversation_id):
            return "conversation-epoch"

        def turn(self, _conversation_id, request):
            schema = (
                "restricted-turn-result.v1"
                if self.status == "COMMITTED"
                else "restricted-turn-status.v1"
            )
            result = {
                "schema_version": schema,
                "turn_id": str(uuid.uuid4()),
                "conversation_epoch": request["conversation_epoch"],
                "status": self.status,
            }
            if self.status == "COMMITTED":
                result["message"] = "synthetic response"
            return result

    store = RestrictedStateStore(tmp_path)
    store.initialize(EPOCH, DIGEST)
    store.write_authority(EPOCH, DIGEST)
    _write_root_restricted_config(tmp_path, RestrictedConfig(True, EPOCH, DIGEST))
    client = Client()
    runner = RestrictedRunner(tmp_path, client)
    runner.start()
    try:
        assert runner.submit("one") == "synthetic response"
        assert store.read_state()["pending_request_id"] is None
        client.status = "INDETERMINATE"
        with pytest.raises(RestrictedPendingError):
            runner.submit("two")
        assert store.read_state()["pending_request_id"] is not None
    finally:
        runner.close()


@pytest.mark.linux_only
@pytest.mark.parametrize(
    ("status", "clears_pending"),
    [
        ("REJECTED", True),
        ("FAILED", True),
        ("INDETERMINATE", False),
        ("RECEIVED", False),
        ("REQUEST_COMMITTED", False),
        ("INFERENCE_PENDING", False),
        ("RESPONSE_RECEIVED", False),
    ],
)
def test_turn_statuses_follow_the_closed_pending_table(
    tmp_path, status, clears_pending
):
    from hermes_cli.restricted_runtime import (
        RESTRICTED_READINESS,
        RestrictedConfig,
        RestrictedPendingError,
        RestrictedRunner,
        RestrictedStateStore,
        RestrictedTurnFailed,
        _write_root_restricted_config,
    )

    class Client:
        def ready(self, epoch, digest):
            return dict(RESTRICTED_READINESS, policy_epoch=epoch, policy_digest=digest)

        def create_conversation(self, _conversation_id):
            return "conversation-epoch"

        def turn(self, _conversation_id, request):
            return {
                "schema_version": "restricted-turn-status.v1",
                "turn_id": str(uuid.uuid4()),
                "conversation_epoch": request["conversation_epoch"],
                "status": status,
            }

    store = RestrictedStateStore(tmp_path)
    store.initialize(EPOCH, DIGEST)
    store.write_authority(EPOCH, DIGEST)
    _write_root_restricted_config(tmp_path, RestrictedConfig(True, EPOCH, DIGEST))
    with RestrictedRunner(tmp_path, Client()) as runner:
        expected_error = (
            RestrictedTurnFailed if clears_pending else RestrictedPendingError
        )
        with pytest.raises(expected_error):
            runner.submit("synthetic")
        assert (store.read_state()["pending_request_id"] is None) is clears_pending
