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


@pytest.mark.parametrize(
    "key",
    [
        '"restricted_runtime"',
        "'restricted_runtime'",
        '"restricted\\u005fruntime"',
        '"restricted\\x5fruntime"',
    ],
)
def test_equivalent_quoted_or_escaped_reserved_keys_are_signals(tmp_path, key):
    from hermes_cli.restricted_bootstrap import config_has_restricted_signal

    path = tmp_path / "config.yaml"
    path.write_text(f"{key}:\n  enabled: true\n", encoding="utf-8")
    assert config_has_restricted_signal(path) is True


@pytest.mark.parametrize(
    "key",
    [
        '"\\x72estricted_runtime"',
        '"restric\\x74ed_runtime"',
        '"restricted_runtim\\x65"',
        '"\\u0072estricted_runtime"',
        '"restric\\u0074ed_runtime"',
        '"restricted_runtim\\u0065"',
        '"\\U00000072estricted_runtime"',
        '"restric\\U00000074ed_runtime"',
        '"restricted_runtim\\U00000065"',
        '"\\u0072estric\\x74ed\\U0000005frunt\\x69me"',
    ],
)
def test_numeric_escapes_cannot_hide_any_reserved_key_character(tmp_path, key):
    from hermes_cli.restricted_bootstrap import config_has_restricted_signal

    path = tmp_path / "config.yaml"
    path.write_text(f"{key}:\n  enabled: true\n", encoding="utf-8")
    assert config_has_restricted_signal(path) is True


@pytest.mark.parametrize(
    "payload",
    [
        '\ufeff"\\u0072estricted_runtime":\n  enabled: true\n',
        '? "restric\\u0074ed_runtime"\n: {enabled: true}\n',
        '"restric\\\n  ted_runtime":\n  enabled: true\n',
    ],
)
def test_escaped_reserved_key_forms_remain_closed_at_yaml_boundaries(tmp_path, payload):
    from hermes_cli.restricted_bootstrap import config_has_restricted_signal

    path = tmp_path / "config.yaml"
    path.write_text(payload, encoding="utf-8")
    assert config_has_restricted_signal(path) is True


@pytest.mark.parametrize(
    "payload",
    [
        '# "restric\\u0074ed_runtime": is only a comment\nmodel: normal\n',
        "'restric\\u0074ed_runtime': literal-backslash-key\nmodel: normal\n",
        'description: "\\\\u0072estricted_runtime"\nmodel: normal\n',
    ],
)
def test_nonsemantic_or_literal_backslash_spelling_is_not_a_signal(tmp_path, payload):
    from hermes_cli.restricted_bootstrap import config_has_restricted_signal

    path = tmp_path / "config.yaml"
    path.write_text(payload, encoding="utf-8")
    assert config_has_restricted_signal(path) is False


@pytest.mark.parametrize(
    "payload",
    [
        'description: "restric\\u0074ed_runtime"\nmodel: normal\n',
        ('name: &reserved "restric\\u0074ed_runtime"\n*reserved:\n  enabled: true\n'),
    ],
)
def test_escaped_reserved_value_is_a_conservative_alias_safe_signal(tmp_path, payload):
    from hermes_cli.restricted_bootstrap import config_has_restricted_signal

    path = tmp_path / "config.yaml"
    path.write_text(payload, encoding="utf-8")
    assert config_has_restricted_signal(path) is True


def test_scanner_holds_one_config_snapshot_across_atomic_replace(tmp_path):
    from hermes_cli.restricted_bootstrap import RestrictedBootstrapScanner
    from hermes_cli.restricted_runtime import RestrictedYamlConfigLoader

    path = tmp_path / "config.yaml"
    path.write_text(
        '"restric\\u0074ed_runtime":\n'
        "  enabled: true\n"
        "  expected_policy_epoch: snapshot-policy\n"
        f"  expected_policy_digest: {'a' * 64}\n",
        encoding="utf-8",
    )
    scanner = RestrictedBootstrapScanner(argv=["chat"], config_path=path)
    replacement = tmp_path / "replacement.yaml"
    replacement.write_text("model: normal\n", encoding="utf-8")
    replacement.replace(path)

    assert scanner.config_signal is True
    assert (
        RestrictedYamlConfigLoader(path, snapshot=scanner.config_snapshot)
        .load()
        .enabled
        is True
    )


@pytest.mark.linux_only
def test_wrapper_cannot_degrade_closed_snapshot_after_replace(
    tmp_path, monkeypatch, capsys
):
    import hermes_cli.restricted_entry as entry

    path = tmp_path / "config.yaml"
    path.write_text(
        "restricted_runtime:\n"
        "  enabled: true\n"
        "  expected_policy_epoch: snapshot-policy\n"
        f"  expected_policy_digest: {'b' * 64}\n",
        encoding="utf-8",
    )
    original = entry._prepare_closed_runtime

    def replace_then_prepare(root, snapshot):
        replacement = tmp_path / "normal.yaml"
        replacement.write_text("model: normal\n", encoding="utf-8")
        replacement.replace(path)
        return original(root, snapshot)

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setattr(sys, "argv", ["hermes", "gateway"])
    monkeypatch.setattr(entry, "_prepare_closed_runtime", replace_then_prepare)
    monkeypatch.setattr(
        entry.FullHermesArgparseParser,
        "run",
        staticmethod(lambda: (_ for _ in ()).throw(AssertionError("normal path"))),
    )
    with pytest.raises(SystemExit) as raised:
        entry.main()
    assert raised.value.code == 77
    assert capsys.readouterr().err == "RESTRICTED_ENTRYPOINT_BLOCKED\n"
    assert (tmp_path / "restricted-runtime" / "enabled").exists()


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


@pytest.mark.parametrize(
    "payload",
    [
        "# restricted_runtime example only\nmodel: nous\n",
        'description: "restric\\u0074ed_runtime"\nmodel: nous\n',
    ],
)
def test_conservative_signal_resolves_safely_then_uses_normal_path(
    tmp_path, monkeypatch, payload
):
    import hermes_cli.restricted_entry as entry

    (tmp_path / "config.yaml").write_text(payload, encoding="utf-8")
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
