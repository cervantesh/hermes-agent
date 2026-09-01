import os
import subprocess
import sys

import pytest


EPOCH = "policy-entrypoint"
DIGEST = "d" * 64


def _armed_root(tmp_path):
    from hermes_cli.restricted_runtime import (
        RestrictedConfig,
        RestrictedStateStore,
        _write_root_restricted_config,
    )

    store = RestrictedStateStore(tmp_path)
    store.initialize(EPOCH, DIGEST)
    store.write_authority(EPOCH, DIGEST)
    _write_root_restricted_config(tmp_path, RestrictedConfig(True, EPOCH, DIGEST))
    return tmp_path


@pytest.mark.linux_only
def test_import_run_agent_is_blocked_before_model_tools(tmp_path):
    _armed_root(tmp_path)
    env = os.environ.copy()
    env["HERMES_HOME"] = str(tmp_path)
    code = "import sys; import run_agent; raise SystemExit('unreachable')"
    result = subprocess.run(
        [sys.executable, "-c", code], text=True, capture_output=True, env=env
    )
    assert result.returncode == 77
    assert result.stderr == "RESTRICTED_ENTRYPOINT_BLOCKED\n"
    assert result.stdout == ""


@pytest.mark.linux_only
def test_armed_installation_blocks_the_subprocess_matrix(tmp_path):
    _armed_root(tmp_path)
    env = os.environ.copy()
    env["HERMES_HOME"] = str(tmp_path)
    wrapper = "from hermes_cli.restricted_entry import main; main()"
    commands = [
        [sys.executable, "-c", wrapper, "--tui"],
        [sys.executable, "-c", wrapper, "gateway"],
        [sys.executable, "-c", wrapper, "cron", "tick"],
        [sys.executable, "-c", "import run_agent"],
        [sys.executable, "-c", "import acp_adapter.entry"],
        [sys.executable, "-m", "gateway.run"],
        [sys.executable, "-m", "tui_gateway.entry"],
        [sys.executable, "-m", "acp_adapter.entry"],
        [sys.executable, "-m", "cron.scheduler"],
        [sys.executable, "run_agent.py"],
    ]
    for command in commands:
        result = subprocess.run(command, text=True, capture_output=True, env=env)
        assert (result.returncode, result.stdout, result.stderr) == (
            77,
            "",
            "RESTRICTED_ENTRYPOINT_BLOCKED\n",
        ), command


@pytest.mark.linux_only
def test_armed_wrapper_rejects_bare_pipe_and_normal_escape_arguments(tmp_path):
    _armed_root(tmp_path)
    env = os.environ.copy()
    env["HERMES_HOME"] = str(tmp_path)
    wrapper = "from hermes_cli.restricted_entry import main; main()"

    bare = subprocess.run(
        [sys.executable, "-c", wrapper],
        input="",
        text=True,
        capture_output=True,
        env=env,
    )
    assert (bare.returncode, bare.stdout, bare.stderr) == (
        64,
        "",
        "RESTRICTED_USAGE_ERROR\n",
    )

    for argv in (
        ["--safe-mode"],
        ["--ignore-user-config"],
        ["chat", "--model", "unsafe"],
    ):
        blocked = subprocess.run(
            [sys.executable, "-c", wrapper, *argv],
            input="",
            text=True,
            capture_output=True,
            env=env,
        )
        assert (blocked.returncode, blocked.stdout, blocked.stderr) == (
            77,
            "",
            "RESTRICTED_ENTRYPOINT_BLOCKED\n",
        )


@pytest.mark.linux_only
def test_run_agent_guard_precedes_model_tools_side_effect(tmp_path):
    _armed_root(tmp_path)
    sentinel = tmp_path / "model-tools-imported"
    (tmp_path / "model_tools.py").write_text(
        f"from pathlib import Path\nPath({str(sentinel)!r}).write_text('bad')\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["HERMES_HOME"] = str(tmp_path)
    env["PYTHONPATH"] = os.pathsep.join([str(tmp_path), os.getcwd()])
    result = subprocess.run(
        [sys.executable, "-c", "import run_agent"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        env=env,
    )
    assert result.returncode == 77
    assert result.stderr == "RESTRICTED_ENTRYPOINT_BLOCKED\n"
    assert not sentinel.exists()


@pytest.mark.linux_only
def test_wrapper_rejects_invalid_authority_before_yaml_import(tmp_path):
    authority_dir = tmp_path / "restricted-runtime"
    authority_dir.mkdir(mode=0o700)
    authority = authority_dir / "enabled"
    authority.write_text("invalid", encoding="utf-8")
    os.chmod(authority, 0o640)
    sentinel = tmp_path / "yaml-imported"
    (tmp_path / "yaml.py").write_text(
        f"from pathlib import Path\nPath({str(sentinel)!r}).write_text('bad')\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["HERMES_HOME"] = str(tmp_path)
    env["PYTHONPATH"] = os.pathsep.join([str(tmp_path), os.getcwd()])
    wrapper = "from hermes_cli.restricted_entry import main; main()"
    result = subprocess.run(
        [sys.executable, "-c", wrapper, "restricted", "status"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        env=env,
    )
    assert (result.returncode, result.stdout, result.stderr) == (
        78,
        "",
        "RESTRICTED_AUTHORITY_INVALID\n",
    )
    assert not sentinel.exists()


@pytest.mark.linux_only
def test_python_m_main_delegates_before_early_import_side_effects(tmp_path):
    _armed_root(tmp_path)
    sentinel = tmp_path / "early-imported"
    (tmp_path / "sitecustomize.py").write_text(
        "import sys, types\n"
        "class Sentinel(types.ModuleType):\n"
        "    def __getattr__(self, name):\n"
        f"        open({str(sentinel)!r}, 'w').write(name)\n"
        "        return lambda *args, **kwargs: None\n"
        "sys.modules['hermes_cli._subprocess_compat'] = Sentinel('hermes_cli._subprocess_compat')\n"
        "sys.modules['hermes_cli.cli_output'] = Sentinel('hermes_cli.cli_output')\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["HERMES_HOME"] = str(tmp_path)
    env["PYTHONPATH"] = os.pathsep.join([str(tmp_path), os.getcwd()])
    result = subprocess.run(
        [sys.executable, "-m", "hermes_cli.main", "gateway"],
        text=True,
        capture_output=True,
        env=env,
    )
    assert (result.returncode, result.stdout, result.stderr) == (
        77,
        "",
        "RESTRICTED_ENTRYPOINT_BLOCKED\n",
    )
    assert not sentinel.exists()


@pytest.mark.linux_only
def test_installed_console_script_uses_restricted_wrapper(tmp_path):
    import shutil

    _armed_root(tmp_path)
    console_script = shutil.which("hermes")
    assert console_script is not None
    env = os.environ.copy()
    env["HERMES_HOME"] = str(tmp_path)
    result = subprocess.run(
        [console_script, "gateway"], text=True, capture_output=True, env=env
    )
    assert (result.returncode, result.stdout, result.stderr) == (
        77,
        "",
        "RESTRICTED_ENTRYPOINT_BLOCKED\n",
    )


@pytest.mark.linux_only
def test_disable_restores_every_direct_guarded_entrypoint(tmp_path):
    from hermes_cli.restricted_runtime import restricted_disable

    _armed_root(tmp_path)
    restricted_disable(tmp_path)
    sentinel = tmp_path / "guard-passed"
    (tmp_path / "sitecustomize.py").write_text(
        "import os\n"
        "from pathlib import Path\n"
        "import hermes_cli.restricted_bootstrap as rb\n"
        "original = rb.guard_restricted_entrypoint\n"
        "def observed(*args, **kwargs):\n"
        "    original(*args, **kwargs)\n"
        "    Path(os.environ['RESTRICTED_GUARD_SENTINEL']).write_text('passed')\n"
        "rb.guard_restricted_entrypoint = observed\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["HERMES_HOME"] = str(tmp_path)
    env["PYTHONPATH"] = os.pathsep.join([str(tmp_path), os.getcwd()])
    env["RESTRICTED_GUARD_SENTINEL"] = str(sentinel)
    for module in (
        "run_agent",
        "gateway.run",
        "tui_gateway.entry",
        "acp_adapter.entry",
        "cron.scheduler",
    ):
        sentinel.unlink(missing_ok=True)
        subprocess.run(
            [sys.executable, "-c", f"import {module}"],
            text=True,
            capture_output=True,
            env=env,
            timeout=20,
        )
        assert sentinel.read_text(encoding="utf-8") == "passed", module


@pytest.mark.linux_only
def test_preimported_agent_reference_is_blocked_after_enable(tmp_path):
    env = os.environ.copy()
    env["HERMES_HOME"] = str(tmp_path)
    code = f"""
import run_agent
from hermes_cli.restricted_runtime import RestrictedConfig, RestrictedStateStore, _write_root_restricted_config
root = __import__('pathlib').Path({str(tmp_path)!r})
store = RestrictedStateStore(root)
store.initialize({EPOCH!r}, {DIGEST!r})
store.write_authority({EPOCH!r}, {DIGEST!r})
_write_root_restricted_config(root, RestrictedConfig(True, {EPOCH!r}, {DIGEST!r}))
run_agent.AIAgent()
"""
    result = subprocess.run(
        [sys.executable, "-c", code], text=True, capture_output=True, env=env
    )
    assert result.returncode == 77
    assert result.stderr == "RESTRICTED_ENTRYPOINT_BLOCKED\n"
