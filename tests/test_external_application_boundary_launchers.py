from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from hermes_application_boundary import _build_marker, _strict_atomic_json_write


ROOT = Path(__file__).resolve().parents[1]


LAUNCHERS = [
    [sys.executable, "-m", "hermes_cli.main", "chat", "sentinel-arg"],
    [sys.executable, os.fspath(ROOT / "run_agent.py"), "--query", "sentinel-arg"],
    [sys.executable, "-m", "acp_adapter.entry", "sentinel-arg"],
    [sys.executable, "-m", "gateway.run", "sentinel-arg"],
    [sys.executable, "-m", "tui_gateway.entry", "sentinel-arg"],
    [sys.executable, os.fspath(ROOT / "batch_runner.py"), "sentinel-arg"],
    [sys.executable, os.fspath(ROOT / "cron" / "scheduler.py"), "sentinel-arg"],
    [sys.executable, os.fspath(ROOT / "cli.py"), "sentinel-arg"],
    [sys.executable, "-m", "cli", "sentinel-arg"],
]

GUARDED_LAUNCHERS = [
    [sys.executable, "-S", os.fspath(ROOT / "batch_runner.py"), "sentinel-arg"],
    [sys.executable, "-S", "-m", "acp_adapter.entry", "sentinel-arg"],
    [sys.executable, "-S", os.fspath(ROOT / "cli.py"), "sentinel-arg"],
    [sys.executable, "-S", os.fspath(ROOT / "run_agent.py"), "sentinel-arg"],
    [sys.executable, "-S", "-m", "gateway.run", "sentinel-arg"],
    [sys.executable, "-S", "-m", "hermes_cli.main", "chat", "sentinel-arg"],
]


def _armed_home(tmp_path: Path) -> tuple[Path, Path]:
    home = tmp_path / "home"
    out = tmp_path / "observed.json"
    handler = tmp_path / "handler.py"
    handler.write_text(
        "import json, os, sys\n"
        "data={'argv':sys.argv[1:], 'stdin':sys.stdin.read(), "
        "'recursion':os.environ.get('_HERMES_EXTERNAL_APPLICATION_ACTIVE')}\n"
        "open(os.environ['BOUNDARY_OUT'],'w',encoding='utf-8').write(json.dumps(data))\n"
        "print('delegated-output')\n"
        "raise SystemExit(23)\n",
        encoding="utf-8",
    )
    command = [sys.executable, os.fspath(handler)]
    home.mkdir()
    (home / "config.yaml").write_text(
        "application:\n  external:\n    command:\n"
        + "".join(f"      - {json.dumps(part)}\n" for part in command),
        encoding="utf-8",
    )
    marker = home / "state" / "application-boundary.json"
    _strict_atomic_json_write(marker, _build_marker(command))
    return home, out


def _assert_armed_delegation(tmp_path: Path, argv: list[str]) -> None:
    home, out = _armed_home(tmp_path)
    env = os.environ.copy()
    env.update(HERMES_HOME=os.fspath(home), BOUNDARY_OUT=os.fspath(out))
    env.pop("_HERMES_EXTERNAL_APPLICATION_ACTIVE", None)
    proc = subprocess.run(
        argv,
        cwd=ROOT,
        env=env,
        input="inherited-input",
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert proc.returncode == 23, proc.stderr
    assert "delegated-output" in proc.stdout
    observed = json.loads(out.read_text(encoding="utf-8"))
    assert "sentinel-arg" in observed["argv"]
    assert observed["stdin"] == "inherited-input"
    assert observed["recursion"] == "1"


@pytest.mark.parametrize("argv", LAUNCHERS)
def test_every_launcher_delegates_before_normal_lifecycle(tmp_path, argv):
    _assert_armed_delegation(tmp_path, argv)


@pytest.mark.windows_only
@pytest.mark.parametrize("argv", LAUNCHERS)
def test_native_windows_armed_delegation_preserves_exact_exit(tmp_path, argv):
    _assert_armed_delegation(tmp_path, argv)


@pytest.mark.macos_only
@pytest.mark.parametrize("argv", LAUNCHERS)
def test_native_macos_armed_delegation_preserves_exact_exit(tmp_path, argv):
    _assert_armed_delegation(tmp_path, argv)


@pytest.mark.parametrize("argv", LAUNCHERS)
def test_marker_absent_reaches_each_normal_launcher_path(tmp_path, argv):
    home = tmp_path / "home"
    home.mkdir()
    out = tmp_path / "must-not-exist.json"
    env = os.environ.copy()
    env.update(HERMES_HOME=os.fspath(home), BOUNDARY_OUT=os.fspath(out))
    env.pop("_HERMES_EXTERNAL_APPLICATION_ACTIVE", None)
    proc = subprocess.run(
        argv,
        cwd=ROOT,
        env=env,
        input="",
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=20,
    )
    assert proc.returncode != 23
    assert "delegated-output" not in proc.stdout
    assert not out.exists()


@pytest.mark.parametrize("statement", ["import run_agent", "import gateway"])
def test_library_import_from_unrelated_program_does_not_delegate(tmp_path, statement):
    home, out = _armed_home(tmp_path)
    env = os.environ.copy()
    env.update(HERMES_HOME=os.fspath(home), BOUNDARY_OUT=os.fspath(out))
    env.pop("_HERMES_EXTERNAL_APPLICATION_ACTIVE", None)
    proc = subprocess.run(
        [sys.executable, "-c", f"{statement}; print('library-ok')"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert proc.returncode == 0, proc.stderr
    assert "library-ok" in proc.stdout
    assert not out.exists()


def test_invalid_marker_rejects_before_normal_launcher_imports(tmp_path):
    home = tmp_path / "home"
    marker = home / "state" / "application-boundary.json"
    marker.parent.mkdir(parents=True)
    marker.write_text("{", encoding="utf-8")
    sentinel = tmp_path / "normal-lifecycle.txt"
    env = os.environ.copy()
    env.update(HERMES_HOME=os.fspath(home), NORMAL_LIFECYCLE_SENTINEL=os.fspath(sentinel))
    proc = subprocess.run(
        [sys.executable, "-m", "gateway.run", "sentinel-arg"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert proc.returncode != 0
    assert "boundary rejected" in proc.stderr.lower()
    assert not sentinel.exists()


@pytest.mark.parametrize("argv", GUARDED_LAUNCHERS)
def test_guarded_bootstrap_import_never_swallows_transitive_missing_dependency(tmp_path, argv):
    home, out = _armed_home(tmp_path)
    env = os.environ.copy()
    env.update(HERMES_HOME=os.fspath(home), BOUNDARY_OUT=os.fspath(out))
    env.pop("_HERMES_EXTERNAL_APPLICATION_ACTIVE", None)
    proc = subprocess.run(
        argv,
        cwd=ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=20,
    )
    assert proc.returncode != 0
    assert "No module named 'yaml'" in proc.stderr
    assert "No module named 'rich'" not in proc.stderr
    assert not out.exists()


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        (["application", "status"], 1),
        (["application", "enable"], 0),
        (["application", "disable"], 0),
        (["--version"], 0),
    ],
)
def test_gate_owned_recovery_bypasses_invalid_marker(tmp_path, arguments, expected):
    home = tmp_path / "home"
    handler = tmp_path / "handler.py"
    handler.write_text("raise SystemExit(99)\n", encoding="utf-8")
    home.mkdir()
    (home / "config.yaml").write_text(
        "application:\n  external:\n    command:\n"
        f"      - {json.dumps(sys.executable)}\n"
        f"      - {json.dumps(os.fspath(handler))}\n",
        encoding="utf-8",
    )
    marker = home / "state" / "application-boundary.json"
    marker.parent.mkdir()
    marker.write_text("{", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "hermes_cli.main", *arguments],
        cwd=ROOT,
        env={**os.environ, "HERMES_HOME": os.fspath(home)},
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert proc.returncode == expected, proc.stderr
