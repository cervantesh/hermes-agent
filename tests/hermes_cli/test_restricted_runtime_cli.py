import pytest


def test_nonclaims_are_always_false():
    from hermes_cli.restricted_runtime import NONCLAIMS

    assert NONCLAIMS == {
        "deployment_conformant": False,
        "model_attested": False,
        "phi_authorized": False,
    }
    with pytest.raises(TypeError):
        NONCLAIMS["phi_authorized"] = True


def test_one_shot_requires_non_tty_stdin_and_no_payload():
    from hermes_cli.restricted_runtime import (
        RestrictedUsageError,
        validate_stdin_invocation,
    )

    validate_stdin_invocation(["--stdin"], stdin_isatty=False)
    for argv, isatty in [
        (["--stdin", "payload"], False),
        (["--stdin"], True),
        ([], False),
    ]:
        try:
            validate_stdin_invocation(argv, stdin_isatty=isatty)
        except RestrictedUsageError:
            pass
        else:
            raise AssertionError((argv, isatty))


def test_restricted_parser_rejects_extra_payload_without_printing(capsys):
    from hermes_cli.restricted_runtime import RestrictedUsageError
    from hermes_cli.subcommands.restricted import parse_restricted_invocation

    with pytest.raises(RestrictedUsageError):
        parse_restricted_invocation(("run", "--stdin", "payload"))
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_default_config_declares_disabled_restricted_mode():
    from hermes_cli.config_defaults import DEFAULT_CONFIG

    assert DEFAULT_CONFIG["restricted_runtime"] == {
        "enabled": False,
        "expected_policy_epoch": None,
        "expected_policy_digest": None,
    }


def test_public_failure_classes_have_closed_symbols_and_codes():
    from hermes_cli.restricted_runtime import (
        RestrictedAuthorityError,
        RestrictedEntrypointBlocked,
        RestrictedPendingError,
        RestrictedPlatformError,
        RestrictedPolicyMismatch,
        RestrictedRuntimeUnavailable,
        RestrictedTurnFailed,
        RestrictedUsageError,
    )

    assert [
        (cls.exit_code, cls.symbol)
        for cls in (
            RestrictedUsageError,
            RestrictedPlatformError,
            RestrictedTurnFailed,
            RestrictedRuntimeUnavailable,
            RestrictedPendingError,
            RestrictedPolicyMismatch,
            RestrictedEntrypointBlocked,
            RestrictedAuthorityError,
        )
    ] == [
        (64, "RESTRICTED_USAGE_ERROR"),
        (69, "RESTRICTED_PLATFORM_UNSUPPORTED"),
        (70, "RESTRICTED_TURN_FAILED"),
        (74, "RESTRICTED_RUNTIME_UNAVAILABLE"),
        (75, "RESTRICTED_PENDING_AMBIGUOUS"),
        (76, "RESTRICTED_POLICY_MISMATCH"),
        (77, "RESTRICTED_ENTRYPOINT_BLOCKED"),
        (78, "RESTRICTED_AUTHORITY_INVALID"),
    ]
