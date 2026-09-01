import hashlib
import json
import os
import stat

import pytest


EPOCH = "policy-2026-08-31"
DIGEST = "a" * 64


def test_yaml_loader_accepts_only_the_closed_block(tmp_path):
    from hermes_cli.restricted_runtime import RestrictedYamlConfigLoader

    path = tmp_path / "config.yaml"
    path.write_text(
        "restricted_runtime:\n"
        "  enabled: true\n"
        f"  expected_policy_epoch: {EPOCH}\n"
        f"  expected_policy_digest: {DIGEST}\n",
        encoding="utf-8",
    )
    config = RestrictedYamlConfigLoader(path).load()
    assert config.enabled is True
    assert config.expected_policy_epoch == EPOCH
    assert config.expected_policy_digest == DIGEST


def test_yaml_loader_rejects_unknown_key(tmp_path):
    from hermes_cli.restricted_runtime import (
        RestrictedAuthorityError,
        RestrictedYamlConfigLoader,
    )

    path = tmp_path / "config.yaml"
    path.write_text(
        "restricted_runtime:\n  enabled: false\n  socket: /tmp/unsafe.sock\n",
        encoding="utf-8",
    )
    with pytest.raises(RestrictedAuthorityError):
        RestrictedYamlConfigLoader(path).load()


@pytest.mark.linux_only
def test_authority_artifacts_are_private_and_message_is_never_persisted(tmp_path):
    from hermes_cli.restricted_runtime import RestrictedStateStore

    store = RestrictedStateStore(tmp_path)
    store.initialize(EPOCH, DIGEST)
    store.persist_pending(
        "private synthetic message", request_id="4b9c43c5-2db5-4fef-a733-53b87fba9836"
    )

    state_path = tmp_path / "restricted-runtime" / "session.json"
    raw = state_path.read_text(encoding="utf-8")
    assert "private synthetic message" not in raw
    state = json.loads(raw)
    assert state["pending_request_id"] == "4b9c43c5-2db5-4fef-a733-53b87fba9836"
    assert len(state["pending_message_hmac_sha256"]) == 64
    assert stat.S_IMODE(os.lstat(state_path).st_mode) == 0o600
    key = (tmp_path / "restricted-runtime" / "message-hmac.key").read_bytes()
    assert len(key) == 32
    assert state["hmac_key_fingerprint_sha256"] == hashlib.sha256(key).hexdigest()


@pytest.mark.linux_only
def test_same_pending_message_reuses_request_id_and_different_message_stops(tmp_path):
    from hermes_cli.restricted_runtime import (
        RestrictedPendingError,
        RestrictedStateStore,
    )

    store = RestrictedStateStore(tmp_path)
    store.initialize(EPOCH, DIGEST)
    request_id = store.persist_pending(
        "same", request_id="f2f69564-d684-45a4-b94e-b7b04fe1aacd"
    )
    assert store.persist_pending("same") == request_id
    with pytest.raises(RestrictedPendingError):
        store.persist_pending("different")


@pytest.mark.linux_only
def test_interrupted_disable_status_is_inspectable_but_runner_is_not(tmp_path):
    from hermes_cli.restricted_runtime import (
        RestrictedAuthorityError,
        RestrictedConfig,
        RestrictedRunner,
        RestrictedStateStore,
        _write_root_restricted_config,
        restricted_status,
    )

    store = RestrictedStateStore(tmp_path)
    store.initialize(EPOCH, DIGEST)
    store.write_authority(EPOCH, DIGEST)
    _write_root_restricted_config(tmp_path, RestrictedConfig(False, None, None))
    status = restricted_status(tmp_path)
    assert status["configured"] is False
    assert status["armed"] is True
    with pytest.raises(RestrictedAuthorityError):
        RestrictedRunner(tmp_path).start()


@pytest.mark.linux_only
def test_private_state_rejects_wrong_mode_symlink_and_rotated_key(tmp_path):
    from hermes_cli.restricted_runtime import (
        RestrictedAuthorityError,
        RestrictedStateStore,
    )

    store = RestrictedStateStore(tmp_path)
    store.initialize(EPOCH, DIGEST)
    os.chmod(store.session_path, 0o640)
    with pytest.raises(RestrictedAuthorityError):
        store.read_state()

    os.chmod(store.session_path, 0o600)
    store.key_path.write_bytes(b"x" * 32)
    os.chmod(store.key_path, 0o600)
    with pytest.raises(RestrictedAuthorityError):
        store.read_state()

    store.key_path.unlink()
    store.key_path.symlink_to(store.session_path)
    with pytest.raises(RestrictedAuthorityError):
        store.read_state()


@pytest.mark.linux_only
def test_runner_lock_is_global_and_exclusive(tmp_path):
    from hermes_cli.restricted_runtime import (
        RestrictedAuthorityError,
        RestrictedStateStore,
    )

    store = RestrictedStateStore(tmp_path)
    store.initialize(EPOCH, DIGEST)
    first = store.acquire_runner_lock()
    try:
        with pytest.raises(RestrictedAuthorityError):
            RestrictedStateStore(tmp_path).acquire_runner_lock()
    finally:
        first.close()


@pytest.mark.linux_only
def test_failed_file_fsync_does_not_replace_existing_state(tmp_path, monkeypatch):
    from hermes_cli.restricted_runtime import (
        RestrictedAuthorityError,
        RestrictedStateStore,
    )

    store = RestrictedStateStore(tmp_path)
    store.initialize(EPOCH, DIGEST)
    before = store.session_path.read_bytes()
    state = store.read_state()
    state["conversation_epoch"] = "must-not-publish"

    def fail_fsync(_fd):
        raise OSError("synthetic fsync failure")

    monkeypatch.setattr(os, "fsync", fail_fsync)
    with pytest.raises(RestrictedAuthorityError):
        store.write_state(state)
    assert store.session_path.read_bytes() == before


@pytest.mark.linux_only
def test_enable_validates_runtime_before_publishing_any_authority(tmp_path):
    from hermes_cli.restricted_runtime import (
        RestrictedPolicyMismatch,
        restricted_enable,
    )

    class RejectingClient:
        def ready(self, _epoch, _digest):
            assert not (tmp_path / "restricted-runtime").exists()
            raise RestrictedPolicyMismatch()

    with pytest.raises(RestrictedPolicyMismatch):
        restricted_enable(
            EPOCH,
            DIGEST,
            confirm_stopped=True,
            root=tmp_path,
            client=RejectingClient(),
        )
    assert not (tmp_path / "restricted-runtime").exists()
    assert not (tmp_path / "config.yaml").exists()
