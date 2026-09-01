from pathlib import Path
import importlib
import sys

import pytest


def test_scanner_routes_only_closed_restricted_commands(tmp_path):
    from hermes_cli.restricted_bootstrap import RestrictedBootstrapScanner

    scanner = RestrictedBootstrapScanner(
        argv=["restricted", "run", "--stdin"], config_path=tmp_path / "config.yaml"
    )
    assert scanner.restricted_invocation == ("run", "--stdin")
    assert scanner.route_is_closed is True


def test_scanner_treats_reserved_name_as_signal_not_yaml(tmp_path):
    from hermes_cli.restricted_bootstrap import RestrictedBootstrapScanner

    path = tmp_path / "config.yaml"
    path.write_text(
        "# restricted_runtime is documented here\nmodel: nous\n", encoding="utf-8"
    )
    scanner = RestrictedBootstrapScanner(argv=["chat"], config_path=path)
    assert scanner.config_signal is True
    assert scanner.route_is_closed is True


def test_config_signal_cannot_hide_across_read_boundary(tmp_path):
    from hermes_cli.restricted_bootstrap import config_has_restricted_signal

    path = tmp_path / "config.yaml"
    prefix = b"#" * (64 * 1024 - 7)
    path.write_bytes(prefix + b"restricted_runtime:\n  enabled: true\n")
    assert config_has_restricted_signal(path) is True


def test_global_root_is_shared_by_named_profiles(tmp_path):
    from hermes_cli.restricted_bootstrap import resolve_global_hermes_root

    root = tmp_path / "installation"
    assert (
        resolve_global_hermes_root(str(root / "profiles" / "alpha"), native_home=root)
        == root
    )
    assert (
        resolve_global_hermes_root(str(root / "profiles" / "beta"), native_home=root)
        == root
    )


def test_external_custom_home_is_an_independent_root(tmp_path):
    from hermes_cli.restricted_bootstrap import resolve_global_hermes_root

    native = tmp_path / "native"
    custom = tmp_path / "external"
    assert resolve_global_hermes_root(str(custom), native_home=native) == custom


@pytest.mark.linux_only
def test_named_profiles_share_one_armed_authority(tmp_path, monkeypatch):
    from hermes_cli.restricted_bootstrap import should_block_normal_entrypoint
    from hermes_cli.restricted_runtime import RestrictedStateStore

    root = tmp_path / "installation"
    store = RestrictedStateStore(root)
    store.initialize("profile-policy", "e" * 64)
    store.write_authority("profile-policy", "e" * 64)
    for profile in ("alpha", "beta"):
        monkeypatch.setenv("HERMES_HOME", str(root / "profiles" / profile))
        assert should_block_normal_entrypoint() is True


def test_wrapper_import_does_not_import_full_cli_or_yaml(monkeypatch):
    for name in (
        "hermes_cli.restricted_entry",
        "hermes_cli.main",
        "yaml",
        "model_tools",
    ):
        sys.modules.pop(name, None)
    importlib.import_module("hermes_cli.restricted_entry")
    assert "hermes_cli.main" not in sys.modules
    assert "yaml" not in sys.modules
    assert "model_tools" not in sys.modules


def test_comment_signal_resolves_safely_then_uses_normal_path(tmp_path, monkeypatch):
    import hermes_cli.restricted_entry as entry

    (tmp_path / "config.yaml").write_text(
        "# restricted_runtime example only\nmodel: nous\n", encoding="utf-8"
    )
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "argv", ["hermes", "chat"])
    called = []
    monkeypatch.setattr(
        entry.FullHermesArgparseParser, "run", staticmethod(lambda: called.append(True))
    )
    entry.main()
    assert called == [True]


def test_real_invalid_block_fails_closed_before_normal_path(
    tmp_path, monkeypatch, capsys
):
    import hermes_cli.restricted_entry as entry

    (tmp_path / "config.yaml").write_text(
        "restricted_runtime:\n  enabled: true\n  unknown: unsafe\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "argv", ["hermes", "chat"])
    monkeypatch.setattr(
        entry.FullHermesArgparseParser,
        "run",
        staticmethod(
            lambda: (_ for _ in ()).throw(AssertionError("normal CLI imported"))
        ),
    )
    with pytest.raises(SystemExit) as raised:
        entry.main()
    assert raised.value.code == 78
    assert capsys.readouterr().err == "RESTRICTED_AUTHORITY_INVALID\n"


@pytest.mark.linux_only
def test_direct_enabled_config_arms_before_full_cli_import(
    tmp_path, monkeypatch, capsys
):
    import hermes_cli.restricted_entry as entry

    digest = "c" * 64
    (tmp_path / "config.yaml").write_text(
        "restricted_runtime:\n"
        "  enabled: true\n"
        "  expected_policy_epoch: epoch-1\n"
        f"  expected_policy_digest: {digest}\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "argv", ["hermes", "--tui"])
    monkeypatch.setattr(
        entry.FullHermesArgparseParser,
        "run",
        staticmethod(
            lambda: (_ for _ in ()).throw(AssertionError("normal CLI imported"))
        ),
    )
    with pytest.raises(SystemExit) as raised:
        entry.main()
    assert raised.value.code == 77
    assert (tmp_path / "restricted-runtime" / "enabled").exists()
    assert capsys.readouterr().err == "RESTRICTED_ENTRYPOINT_BLOCKED\n"
