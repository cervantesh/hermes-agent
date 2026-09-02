from __future__ import annotations

import json
import os
import subprocess
import sys
import shutil
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
    env.update(
        HERMES_HOME=os.fspath(home),
        BOUNDARY_OUT=os.fspath(out),
        PYTHONPATH=os.fspath(ROOT),
    )
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


@pytest.mark.parametrize("collision_name", ["hermes", "hermes-agent", "hermes-acp"])
@pytest.mark.parametrize("statement", ["import run_agent", "import gateway"])
def test_colliding_argv_basename_cannot_turn_library_import_into_launcher(
    tmp_path, statement, collision_name
):
    home, out = _armed_home(tmp_path)
    collision = tmp_path / collision_name
    collision.write_text(f"{statement}\nprint('library-only')\n", encoding="utf-8")
    env = os.environ.copy()
    env.update(
        HERMES_HOME=os.fspath(home),
        BOUNDARY_OUT=os.fspath(out),
        PYTHONPATH=os.fspath(ROOT),
    )
    env.pop("_HERMES_EXTERNAL_APPLICATION_ACTIVE", None)
    proc = subprocess.run(
        [sys.executable, os.fspath(collision)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert proc.returncode == 0, proc.stderr
    assert "library-only" in proc.stdout
    assert "delegated-output" not in proc.stdout
    assert not out.exists()


@pytest.mark.parametrize("armed", [False, True])
def test_mixed_install_missing_owner_is_marker_aware(tmp_path, armed):
    mixed = tmp_path / "mixed"
    mixed.mkdir()
    (mixed / "hermes_application_boundary.py").write_text(
        "raise ModuleNotFoundError(\"No module named 'hermes_application_boundary'\", "
        "name='hermes_application_boundary')\n",
        encoding="utf-8",
    )
    shutil.copy2(ROOT / "hermes_bootstrap.py", mixed / "hermes_bootstrap.py")
    home = tmp_path / "home"
    if armed:
        marker = home / "state" / "application-boundary.json"
        marker.parent.mkdir(parents=True)
        marker.write_text("{}", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "hermes_cli.main", "--version"],
        cwd=mixed,
        env={
            **os.environ,
            "HERMES_HOME": os.fspath(home),
            "PYTHONPATH": os.pathsep.join([os.fspath(mixed), os.fspath(ROOT)]),
        },
        text=True,
        capture_output=True,
        timeout=20,
    )
    if armed:
        assert proc.returncode != 0
        assert "Hermes Agent" not in proc.stdout
    else:
        assert proc.returncode == 0, proc.stderr
        assert "Hermes Agent" in proc.stdout


def test_profile_subprocess_observes_installation_root_marker(tmp_path):
    root, out = _armed_home(tmp_path)
    profile = root / "profiles" / "coder"
    profile.mkdir(parents=True)
    env = os.environ.copy()
    env.update(HERMES_HOME=os.fspath(profile), BOUNDARY_OUT=os.fspath(out))
    proc = subprocess.run(
        [sys.executable, "-m", "hermes_cli.main", "--profile", "coder", "sentinel-arg"],
        cwd=ROOT,
        env=env,
        input="profile-input",
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert proc.returncode == 23, proc.stderr
    observed = json.loads(out.read_text(encoding="utf-8"))
    assert observed["stdin"] == "profile-input"
    assert ["--profile", "coder", "sentinel-arg"] == observed["argv"]


def test_sticky_profile_subprocess_observes_installation_root_marker(tmp_path):
    root, out = _armed_home(tmp_path)
    (root / "profiles" / "coder").mkdir(parents=True)
    (root / "active_profile").write_text("coder\n", encoding="utf-8")
    env = os.environ.copy()
    env.update(HERMES_HOME=os.fspath(root), BOUNDARY_OUT=os.fspath(out))
    proc = subprocess.run(
        [sys.executable, "-m", "hermes_cli.main", "sentinel-arg"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert proc.returncode == 23, proc.stderr
    assert json.loads(out.read_text(encoding="utf-8"))["argv"] == ["sentinel-arg"]


def test_distinct_custom_root_does_not_observe_armed_installation(tmp_path):
    _root, out = _armed_home(tmp_path)
    custom = tmp_path / "custom-installation"
    custom.mkdir()
    proc = subprocess.run(
        [sys.executable, "-m", "hermes_cli.main", "--version"],
        cwd=ROOT,
        env={**os.environ, "HERMES_HOME": os.fspath(custom), "BOUNDARY_OUT": os.fspath(out)},
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert proc.returncode == 0, proc.stderr
    assert "delegated-output" not in proc.stdout
    assert not out.exists()


def test_process_level_concurrent_enables_publish_complete_marker(tmp_path):
    home = tmp_path / "home"
    handler = tmp_path / "handler.py"
    handler.write_text("raise SystemExit(23)\n", encoding="utf-8")
    home.mkdir()
    (home / "config.yaml").write_text(
        "application:\n  external:\n    command:\n"
        f"      - {json.dumps(sys.executable)}\n"
        f"      - {json.dumps(os.fspath(handler))}\n",
        encoding="utf-8",
    )
    env = {**os.environ, "HERMES_HOME": os.fspath(home)}
    processes = [
        subprocess.Popen(
            [sys.executable, "-m", "hermes_cli.main", "application", "enable"],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        for _ in range(4)
    ]
    results = [process.communicate(timeout=20) + (process.returncode,) for process in processes]
    assert any(result[2] == 0 for result in results), results
    assert all(result[2] in {0, 1} for result in results), results
    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            "import hermes_application_boundary as b; b._validate_armed_state(b.marker_path())",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert probe.returncode == 0, probe.stderr
    assert not list((home / "state").glob("*.tmp"))


def test_armed_gate_precedes_lazy_target_activation(tmp_path):
    home, out = _armed_home(tmp_path)
    sentinel = tmp_path / "lazy-imported"
    fake_tools = tmp_path / "tools"
    fake_tools.mkdir()
    (fake_tools / "__init__.py").write_text("", encoding="utf-8")
    (fake_tools / "lazy_deps.py").write_text(
        "import os\nopen(os.environ['LAZY_SENTINEL'],'w').write('reached')\n"
        "def activate_durable_lazy_target(): pass\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env.update(
        HERMES_HOME=os.fspath(home),
        BOUNDARY_OUT=os.fspath(out),
        HERMES_LAZY_INSTALL_TARGET=os.fspath(tmp_path / "lazy-target"),
        LAZY_SENTINEL=os.fspath(sentinel),
        PYTHONPATH=os.pathsep.join([os.fspath(tmp_path), os.fspath(ROOT)]),
    )
    proc = subprocess.run(
        [sys.executable, "-m", "hermes_cli.main", "sentinel-arg"],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert proc.returncode == 23, proc.stderr
    assert not sentinel.exists()


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


@pytest.mark.windows_only
def test_windows_native_fallback_root_marker_cannot_be_missed(tmp_path):
    userprofile = tmp_path / "profile"
    marker = userprofile / "AppData" / "Local" / "hermes" / "state" / "application-boundary.json"
    marker.parent.mkdir(parents=True)
    marker.write_text("{", encoding="utf-8")
    env = os.environ.copy()
    env.pop("HERMES_HOME", None)
    env.pop("LOCALAPPDATA", None)
    env["USERPROFILE"] = os.fspath(userprofile)
    proc = subprocess.run(
        [sys.executable, "-m", "hermes_cli.main", "chat"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert proc.returncode == 78, proc.stderr
    assert "boundary rejected" in proc.stderr.lower()


@pytest.mark.parametrize(
    "relative",
    [
        "run_agent.py",
        "hermes_cli/main.py",
        "gateway/run.py",
        "acp_adapter/entry.py",
        "tui_gateway/entry.py",
        "cron/scheduler.py",
    ],
)
def test_suffix_collision_script_has_no_launcher_authority(tmp_path, relative):
    home, out = _armed_home(tmp_path)
    script = tmp_path / relative
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text("import hermes_bootstrap\nprint('consumer-ok')\n", encoding="utf-8")
    env = os.environ.copy()
    env.update(
        HERMES_HOME=os.fspath(home),
        BOUNDARY_OUT=os.fspath(out),
        PYTHONPATH=os.fspath(ROOT),
    )
    proc = subprocess.run(
        [sys.executable, os.fspath(script), "sentinel-arg"],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert proc.returncode == 0, proc.stderr
    assert "consumer-ok" in proc.stdout
    assert not out.exists()


def test_gateway_module_pair_in_consumer_arguments_is_not_execution_selector(tmp_path):
    home, out = _armed_home(tmp_path)
    consumer = tmp_path / "consumer.py"
    consumer.write_text("import gateway\nprint('consumer-ok')\n", encoding="utf-8")
    env = os.environ.copy()
    env.update(
        HERMES_HOME=os.fspath(home),
        BOUNDARY_OUT=os.fspath(out),
        PYTHONPATH=os.fspath(ROOT),
    )
    proc = subprocess.run(
        [sys.executable, os.fspath(consumer), "-m", "gateway.run"],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert proc.returncode == 0, proc.stderr
    assert "consumer-ok" in proc.stdout
    assert not out.exists()


def test_gateway_module_pair_after_double_dash_is_not_execution_selector(tmp_path):
    home, out = _armed_home(tmp_path)
    consumer = tmp_path / "-m"
    consumer.write_text("import gateway\nprint('consumer-ok')\n", encoding="utf-8")
    env = os.environ.copy()
    env.update(
        HERMES_HOME=os.fspath(home),
        BOUNDARY_OUT=os.fspath(out),
        PYTHONPATH=os.fspath(ROOT),
    )
    proc = subprocess.run(
        [sys.executable, "--", "-m", "gateway.run"],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert proc.returncode == 0, proc.stderr
    assert "consumer-ok" in proc.stdout
    assert not out.exists()


@pytest.mark.parametrize("marker_state", ["absent", "present", "inaccessible"])
def test_lightweight_shim_missing_owner_is_marker_aware(tmp_path, marker_state):
    mixed = tmp_path / "mixed"
    mixed.mkdir()
    shutil.copy2(ROOT / "hermes_bootstrap.py", mixed / "hermes_bootstrap.py")
    shutil.copy2(ROOT / "hermes_entrypoints.py", mixed / "hermes_entrypoints.py")
    home = tmp_path / "home"
    if marker_state == "present":
        marker = home / "state" / "application-boundary.json"
        marker.parent.mkdir(parents=True)
        marker.write_text("{}", encoding="utf-8")
    statement = "import hermes_entrypoints; hermes_entrypoints._admit('hermes')"
    if marker_state == "inaccessible":
        statement = (
            "import hermes_bootstrap, hermes_entrypoints; "
            "hermes_bootstrap._boundary_marker_is_provably_absent="
            "lambda: (_ for _ in ()).throw(PermissionError('denied')); "
            "hermes_entrypoints._admit('hermes')"
        )
    proc = subprocess.run(
        [sys.executable, "-c", statement],
        cwd=mixed,
        env={**os.environ, "HERMES_HOME": os.fspath(home), "PYTHONPATH": os.fspath(mixed)},
        text=True,
        capture_output=True,
        timeout=20,
    )
    if marker_state == "absent":
        assert proc.returncode == 0, proc.stderr
    elif marker_state == "present":
        assert proc.returncode != 0
    else:
        assert proc.returncode != 0
        assert "PermissionError" in proc.stderr


def test_lightweight_shim_propagates_transitive_owner_dependency_loss(tmp_path):
    mixed = tmp_path / "mixed"
    mixed.mkdir()
    shutil.copy2(ROOT / "hermes_bootstrap.py", mixed / "hermes_bootstrap.py")
    shutil.copy2(ROOT / "hermes_entrypoints.py", mixed / "hermes_entrypoints.py")
    (mixed / "hermes_application_boundary.py").write_text(
        "raise ModuleNotFoundError(\"No module named 'yaml'\", name='yaml')\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, "-c", "import hermes_entrypoints; hermes_entrypoints._admit('hermes')"],
        cwd=mixed,
        env={**os.environ, "HERMES_HOME": os.fspath(tmp_path / "home"), "PYTHONPATH": os.fspath(mixed)},
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert proc.returncode != 0
    assert "No module named 'yaml'" in proc.stderr


@pytest.mark.parametrize(
    "arguments",
    [
        ["application"],
        ["application", "unknown"],
        ["application", "status", "extra"],
        ["application", "enable", "extra"],
        ["application", "disable", "extra"],
    ],
)
def test_unsupported_application_arguments_delegate_when_armed(tmp_path, arguments):
    home, out = _armed_home(tmp_path)
    proc = subprocess.run(
        [sys.executable, "-m", "hermes_cli.main", *arguments],
        cwd=ROOT,
        env={**os.environ, "HERMES_HOME": os.fspath(home), "BOUNDARY_OUT": os.fspath(out)},
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert proc.returncode == 23, proc.stderr
    assert json.loads(out.read_text(encoding="utf-8"))["argv"] == arguments
