from __future__ import annotations

import json
import errno
import os
from pathlib import Path
import subprocess
import sys
import threading

import pytest

import hermes_application_boundary as boundary


def _write_config(root: Path, command: list[str]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "config.yaml").write_text(
        "application:\n  external:\n    command:\n"
        + "".join(f"      - {json.dumps(part)}\n" for part in command),
        encoding="utf-8",
    )


def _handler(tmp_path: Path) -> Path:
    path = tmp_path / "handler.py"
    path.write_text("print('handler')\n", encoding="utf-8")
    return path


def test_marker_absent_does_not_load_yaml(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setattr(boundary, "_load_command", lambda *_: pytest.fail("config parsed"))
    assert boundary.admit(["hermes", "chat"], launcher="hermes") is None


def test_enable_writes_matching_marker_and_disable_removes_it(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    handler = _handler(tmp_path)
    _write_config(tmp_path, [os.fspath(Path(os.sys.executable)), os.fspath(handler)])

    assert boundary.manage(["application", "enable"]) == 0
    marker = boundary.marker_path()
    payload = json.loads(marker.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert set(payload) == {"schema_version", "configuration_digest", "executable"}
    assert boundary._validate_armed_state(marker)[0][0] == os.sys.executable

    assert boundary.manage(["application", "disable"]) == 0
    assert not marker.exists()


@pytest.mark.parametrize(
    "mutator",
    [
        lambda p: p.write_text("{", encoding="utf-8"),
        lambda p: p.write_text('{"schema_version": 999}', encoding="utf-8"),
    ],
)
def test_invalid_present_marker_fails_closed(tmp_path, monkeypatch, mutator):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    marker = boundary.marker_path()
    marker.parent.mkdir(parents=True)
    mutator(marker)
    with pytest.raises(boundary.BoundaryRejected):
        boundary.admit(["hermes", "chat"], launcher="hermes")


def test_config_drift_and_executable_drift_fail_closed(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    handler = _handler(tmp_path)
    _write_config(tmp_path, [os.sys.executable, os.fspath(handler)])
    assert boundary.manage(["application", "enable"]) == 0

    _write_config(tmp_path, [os.sys.executable, os.fspath(handler), "changed"])
    with pytest.raises(boundary.BoundaryRejected):
        boundary._validate_armed_state(boundary.marker_path())

    _write_config(tmp_path, [os.sys.executable, os.fspath(handler)])
    assert boundary.manage(["application", "enable"]) == 0
    Path(os.sys.executable)  # executable identity is the interpreter, not handler.py
    payload = json.loads(boundary.marker_path().read_text(encoding="utf-8"))
    payload["executable"]["sha256"] = "0" * 64
    boundary._strict_atomic_json_write(boundary.marker_path(), payload)
    with pytest.raises(boundary.BoundaryRejected):
        boundary._validate_armed_state(boundary.marker_path())


def test_recursion_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    _write_config(tmp_path, [os.sys.executable, "ignored.py"])
    assert boundary.manage(["application", "enable"]) == 0
    monkeypatch.setenv(boundary._RECURSION_ENV, "1")
    with pytest.raises(boundary.BoundaryRejected):
        boundary.admit(["hermes"], launcher="hermes")


def test_library_argv_is_not_a_supported_launcher():
    assert boundary.detect_launcher(["unrelated-program", "run_agent"]) is None


def test_installation_root_is_shared_by_profiles_and_custom_roots_are_independent(
    tmp_path, monkeypatch
):
    root = tmp_path / "install"
    profile = root / "profiles" / "coder"
    monkeypatch.setenv("HERMES_HOME", str(profile))
    assert boundary.installation_root() == root
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "other"))
    assert boundary.installation_root() == tmp_path / "other"


def test_strict_replace_failure_preserves_previous_marker(tmp_path, monkeypatch):
    target = tmp_path / "marker.json"
    boundary._strict_atomic_json_write(target, {"old": True})
    monkeypatch.setattr(boundary.os, "replace", lambda *_: (_ for _ in ()).throw(PermissionError()))
    with pytest.raises(PermissionError):
        boundary._strict_atomic_json_write(target, {"new": True})
    assert json.loads(target.read_text(encoding="utf-8")) == {"old": True}
    assert not list(tmp_path.glob(".*.tmp"))


def test_disable_failure_preserves_armed_marker(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    handler = _handler(tmp_path)
    _write_config(tmp_path, [os.sys.executable, os.fspath(handler)])
    assert boundary.manage(["application", "enable"]) == 0
    marker = boundary.marker_path()
    original_unlink = Path.unlink

    def refuse(path, *args, **kwargs):
        if path == marker:
            raise PermissionError("busy")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", refuse)
    assert boundary.manage(["application", "disable"]) == 1
    assert marker.exists()


def test_two_concurrent_enables_publish_one_complete_valid_marker(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    handler = _handler(tmp_path)
    _write_config(tmp_path, [os.sys.executable, os.fspath(handler)])
    results: list[int] = []
    threads = [
        threading.Thread(target=lambda: results.append(boundary.manage(["application", "enable"])))
        for _ in range(2)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert results == [0, 0]
    boundary._validate_armed_state(boundary.marker_path())
    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            "import hermes_application_boundary as b; b._validate_armed_state(b.marker_path())",
        ],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "HERMES_HOME": os.fspath(tmp_path)},
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert probe.returncode == 0, probe.stderr


def test_recovery_commands_work_with_invalid_armed_state(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    marker = boundary.marker_path()
    marker.parent.mkdir(parents=True)
    marker.write_text("broken", encoding="utf-8")
    assert boundary.manage(["application", "status"]) == 1
    assert boundary.manage(["application", "disable"]) == 0
    assert not marker.exists()
    assert "invalid" in capsys.readouterr().err


def test_directory_sync_suppresses_only_known_unsupported_error(tmp_path, monkeypatch):
    monkeypatch.setattr(
        boundary.os,
        "open",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError(errno.EINVAL, "unsupported")),
    )
    boundary._sync_directory(tmp_path)


def test_directory_sync_propagates_real_io_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(
        boundary.os,
        "open",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError(errno.EIO, "device error")),
    )
    with pytest.raises(OSError, match="device error"):
        boundary._sync_directory(tmp_path)


@pytest.mark.windows_only
@pytest.mark.parametrize("suffix", [".txt", ".py", ".ps1"])
def test_windows_enable_rejects_non_native_direct_handler(tmp_path, monkeypatch, suffix):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    handler = tmp_path / f"handler{suffix}"
    handler.write_text("exit 0\n", encoding="utf-8")
    _write_config(tmp_path, [os.fspath(handler)])
    assert boundary.manage(["application", "enable"]) == 1
    assert not boundary.marker_path().exists()


def test_enable_reports_armed_uncertainty_after_post_publish_sync_failure(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    handler = _handler(tmp_path)
    _write_config(tmp_path, [os.sys.executable, os.fspath(handler)])
    monkeypatch.setattr(
        boundary,
        "_sync_directory",
        lambda *_: (_ for _ in ()).throw(OSError(errno.EIO, "device error")),
    )
    assert boundary.manage(["application", "enable"]) == 1
    assert boundary.marker_path().exists()
    error = capsys.readouterr().err
    assert "marker is present" in error
    assert "armed" in error
    assert "durability was not confirmed" in error


def test_disable_reports_unarmed_uncertainty_after_post_remove_sync_failure(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    handler = _handler(tmp_path)
    _write_config(tmp_path, [os.sys.executable, os.fspath(handler)])
    assert boundary.manage(["application", "enable"]) == 0
    monkeypatch.setattr(
        boundary,
        "_sync_directory",
        lambda *_: (_ for _ in ()).throw(OSError(errno.EIO, "device error")),
    )
    assert boundary.manage(["application", "disable"]) == 1
    assert not boundary.marker_path().exists()
    error = capsys.readouterr().err
    assert "marker is absent" in error
    assert "unarmed" in error
    assert "durability was not confirmed" in error


def test_missing_owner_probe_never_treats_inaccessible_marker_as_absent(monkeypatch):
    import hermes_bootstrap

    monkeypatch.setattr(
        hermes_bootstrap.os,
        "stat",
        lambda *_: (_ for _ in ()).throw(PermissionError(errno.EACCES, "denied")),
    )
    with pytest.raises(PermissionError, match="denied"):
        hermes_bootstrap._boundary_marker_is_provably_absent()
